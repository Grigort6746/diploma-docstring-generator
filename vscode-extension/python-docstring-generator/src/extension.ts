import * as vscode from 'vscode';

const outputChannelName = 'Python Docstring Generator';
const generateDocstringCommand = 'python-docstring-generator.generateDocstring';
const checkOllamaConnectionCommand = 'python-docstring-generator.checkOllamaConnection';

let outputChannel: vscode.OutputChannel | undefined;

interface ExtensionConfiguration {
	ollamaUrl: string;
	model: string;
	temperature: number;
	numPredict: number;
}

interface OllamaGenerateResponse {
	response?: unknown;
	error?: unknown;
}

interface OllamaTagsResponse {
	models?: Array<{
		name?: unknown;
		model?: unknown;
	}>;
}

class UserFacingError extends Error {
	public constructor(message: string) {
		super(message);
		this.name = 'UserFacingError';
	}
}

export function activate(context: vscode.ExtensionContext) {
	outputChannel = vscode.window.createOutputChannel(outputChannelName);

	const generateDisposable = vscode.commands.registerCommand(generateDocstringCommand, async () => {
		await runGenerateDocstringCommand();
	});

	const checkConnectionDisposable = vscode.commands.registerCommand(checkOllamaConnectionCommand, async () => {
		await runCheckOllamaConnectionCommand();
	});

	context.subscriptions.push(outputChannel, generateDisposable, checkConnectionDisposable);
	log('Extension activated.');
}

export function deactivate() {
	outputChannel?.dispose();
}

async function runGenerateDocstringCommand(): Promise<void> {
	log('Generate docstring command started.');

	const editor = vscode.window.activeTextEditor;

	if (!editor) {
		vscode.window.showWarningMessage('Open a Python file and select a function first.');
		return;
	}

	if (!isPythonDocument(editor.document)) {
		vscode.window.showWarningMessage('The active editor is not a Python file.');
		return;
	}

	const selectedCode = editor.document.getText(editor.selection).trimEnd();

	if (!selectedCode.trim()) {
		vscode.window.showWarningMessage('Select a Python function before generating a docstring.');
		return;
	}

	const signature = findFunctionSignature(selectedCode);

	if (!signature) {
		vscode.window.showWarningMessage('Select a Python function with a single-line def or async def signature.');
		return;
	}

	const signatureDocumentLine = editor.selection.start.line + signature.lineOffset;

	if (hasExistingDocstring(selectedCode, signature.lineOffset)) {
		vscode.window.showWarningMessage('This function already appears to have a docstring.');
		return;
	}

	try {
		const config = getConfiguration();
		const prompt = generatePrompt(selectedCode.trim());

		log(`Selected code length: ${selectedCode.length} characters.`);
		log(`Using Ollama model "${config.model}" at ${config.ollamaUrl}.`);

		const generatedText = await vscode.window.withProgress(
			{
				location: vscode.ProgressLocation.Notification,
				title: 'Generating Python docstring...',
				cancellable: false
			},
			async () => callOllama(config, prompt)
		);

		log('Raw model response before normalization:');
		log(generatedText);

		const docstringContent = normalizeGeneratedDocstring(generatedText);

		if (!docstringContent) {
			throw new UserFacingError('The model returned an empty docstring.');
		}

		const signatureIndent = getLineIndent(editor.document.lineAt(signatureDocumentLine).text) || signature.indent;
		const bodyIndent = signatureIndent + getIndentUnit(editor);
		const insertionText = formatDocstringForInsertion(docstringContent, bodyIndent);
		const insertionPosition = new vscode.Position(signatureDocumentLine + 1, 0);

		const applied = await editor.edit((editBuilder) => {
			editBuilder.insert(insertionPosition, insertionText);
		});

		if (!applied) {
			throw new UserFacingError('Could not insert docstring into the editor.');
		}

		vscode.window.showInformationMessage('Python docstring generated and inserted.');
		log('Generated docstring:');
		log(docstringContent);
	} catch (error) {
		handleCommandError('Failed to generate Python docstring.', error);
	}
}

async function runCheckOllamaConnectionCommand(): Promise<void> {
	log('Check Ollama connection command started.');

	try {
		const config = getConfiguration();
		log(`Checking Ollama at ${config.ollamaUrl} with model "${config.model}".`);

		const modelNames = await vscode.window.withProgress(
			{
				location: vscode.ProgressLocation.Notification,
				title: 'Checking Ollama connection...',
				cancellable: false
			},
			async () => fetchOllamaModels(config)
		);

		if (modelNames.includes(config.model)) {
			vscode.window.showInformationMessage(`Ollama is running. Model "${config.model}" is available.`);
			return;
		}

		vscode.window.showWarningMessage(
			`Model "${config.model}" is not installed or not available in Ollama.`
		);
	} catch (error) {
		handleCommandError('Could not connect to Ollama.', error);
	}
}

function getConfiguration(): ExtensionConfiguration {
	const configuration = vscode.workspace.getConfiguration('pythonDocstringGenerator');
	const ollamaUrlValue = configuration.get<unknown>('ollamaUrl', 'http://localhost:11434');
	const modelValue = configuration.get<unknown>('model', 'qwen2.5-coder:1.5b');
	const temperatureValue = configuration.get<unknown>('temperature', 0.2);
	const numPredictValue = configuration.get<unknown>('numPredict', 256);

	const ollamaUrl = typeof ollamaUrlValue === 'string' ? ollamaUrlValue.trim() : '';
	const model = typeof modelValue === 'string' ? modelValue.trim() : '';

	if (!ollamaUrl) {
		throw new UserFacingError('Ollama URL is empty. Check Python Docstring Generator settings.');
	}

	if (!isHttpUrl(ollamaUrl)) {
		throw new UserFacingError('Ollama URL is invalid. Check Python Docstring Generator settings.');
	}

	if (!model) {
		throw new UserFacingError('Model name is empty. Check Python Docstring Generator settings.');
	}

	if (
		typeof temperatureValue !== 'number' ||
		!Number.isFinite(temperatureValue) ||
		temperatureValue < 0 ||
		temperatureValue > 2
	) {
		throw new UserFacingError('temperature must be a number between 0 and 2.');
	}

	if (
		typeof numPredictValue !== 'number' ||
		!Number.isInteger(numPredictValue) ||
		numPredictValue <= 0
	) {
		throw new UserFacingError('numPredict must be a positive integer.');
	}

	return {
		ollamaUrl,
		model,
		temperature: temperatureValue,
		numPredict: numPredictValue
	};
}

function isHttpUrl(value: string): boolean {
	try {
		const parsedUrl = new URL(value);
		return parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:';
	} catch {
		return false;
	}
}

function generatePrompt(code: string): string {
	return [
		'Generate only a Python docstring for the following function.',
		'',
		'Requirements:',
		'- Use Google-style format.',
		'- Return only the docstring.',
		'- Do not include Markdown.',
		'- Do not repeat the code.',
		'- Document all visible arguments.',
		'- Include Returns if the function returns a value.',
		'- Include Raises only if the function clearly raises exceptions.',
		'- Do not invent behavior that is not visible from the function body or signature.',
		'- Be concise but informative.',
		'',
		'Python function:',
		code
	].join('\n');
}

async function callOllama(config: ExtensionConfiguration, prompt: string): Promise<string> {
	const endpoint = buildOllamaUrl(config.ollamaUrl, 'api/generate');
	const response = await fetchWithTimeout(endpoint, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			model: config.model,
			prompt,
			stream: false,
			options: {
				temperature: config.temperature,
				num_predict: config.numPredict
			}
		})
	}, 60_000);
	const body = await readResponseText(response);

	if (!response.ok) {
		log(`Ollama /api/generate returned HTTP ${response.status}.`);
		log(`Response body: ${body}`);
		throw new UserFacingError(formatOllamaHttpError(response.status, body, config.model));
	}

	const data = parseJsonResponse<OllamaGenerateResponse>(body, 'Ollama /api/generate');

	if (typeof data.error === 'string' && data.error.trim()) {
		log(`Ollama /api/generate error field: ${data.error.trim()}`);
		throw new UserFacingError(formatOllamaErrorMessage(data.error.trim(), config.model));
	}

	if (typeof data.response !== 'string' || !data.response.trim()) {
		log(`Ollama /api/generate response without usable text: ${body}`);
		throw new UserFacingError('Ollama response did not contain generated text.');
	}

	return data.response;
}

async function fetchOllamaModels(config: ExtensionConfiguration): Promise<string[]> {
	const endpoint = buildOllamaUrl(config.ollamaUrl, 'api/tags');
	const response = await fetchWithTimeout(endpoint, {
		method: 'GET'
	}, 10_000);
	const body = await readResponseText(response);

	if (!response.ok) {
		log(`Ollama /api/tags returned HTTP ${response.status}.`);
		log(`Response body: ${body}`);
		throw new UserFacingError(formatOllamaHttpError(response.status, body, config.model));
	}

	const data = parseJsonResponse<OllamaTagsResponse>(body, 'Ollama /api/tags');
	return (data.models ?? [])
		.map((model) => {
			if (typeof model.name === 'string') {
				return model.name;
			}

			if (typeof model.model === 'string') {
				return model.model;
			}

			return undefined;
		})
		.filter((modelName): modelName is string => Boolean(modelName));
}

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
	const controller = new AbortController();
	const timeout = setTimeout(() => controller.abort(), timeoutMs);

	try {
		return await fetch(url, {
			...init,
			signal: controller.signal
		});
	} catch (error) {
		log(`Request to ${url} failed.`);
		logErrorDetails(error);

		if (error instanceof Error && error.name === 'AbortError') {
			throw new UserFacingError(`Request to Ollama timed out after ${Math.round(timeoutMs / 1000)} seconds.`);
		}

		throw new UserFacingError('Ollama is not reachable. Make sure it is running and the URL is correct.');
	} finally {
		clearTimeout(timeout);
	}
}

function buildOllamaUrl(baseUrl: string, endpoint: string): string {
	const normalizedBaseUrl = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
	return new URL(endpoint, normalizedBaseUrl).toString();
}

function formatOllamaHttpError(status: number, body: string, model: string): string {
	const trimmedBody = body.trim();

	if (status === 404) {
		if (isModelNotFoundMessage(trimmedBody)) {
			return `Model "${model}" is not installed in Ollama.`;
		}

		return 'Ollama endpoint was not found. Check the Ollama URL setting.';
	}

	if (isModelNotFoundMessage(trimmedBody)) {
		return `Model "${model}" is not installed in Ollama.`;
	}

	return `Ollama returned HTTP ${status}. Check the Output Channel for details.`;
}

function formatOllamaErrorMessage(errorText: string, model: string): string {
	if (isModelNotFoundMessage(errorText)) {
		return `Model "${model}" is not installed in Ollama.`;
	}

	return `Ollama returned an error: ${errorText}`;
}

function isModelNotFoundMessage(message: string): boolean {
	return /model.*not found|not found.*model|try pulling|pull.*model/i.test(message);
}

function parseJsonResponse<T>(body: string, context: string): T {
	try {
		return JSON.parse(body) as T;
	} catch (error) {
		log(`${context} returned invalid JSON.`);
		log(`Response body: ${body}`);
		logErrorDetails(error);
		throw new UserFacingError(`${context} returned an invalid response.`);
	}
}

async function readResponseText(response: Response): Promise<string> {
	try {
		return await response.text();
	} catch {
		return '';
	}
}

function isPythonDocument(document: vscode.TextDocument): boolean {
	return document.languageId === 'python' || document.fileName.toLowerCase().endsWith('.py');
}

function findFunctionSignature(code: string): { lineOffset: number; indent: string } | undefined {
	const lines = code.split(/\r?\n/);

	for (let index = 0; index < lines.length; index += 1) {
		const line = lines[index];
		const match = /^(\s*)(?:async\s+def|def)\s+.+:\s*(?:#.*)?$/.exec(line);

		if (match) {
			return {
				lineOffset: index,
				indent: match[1]
			};
		}
	}

	return undefined;
}

function hasExistingDocstring(code: string, signatureLineOffset: number): boolean {
	const lines = code.split(/\r?\n/);
	const signatureLine = lines[signatureLineOffset];

	if (!signatureLine) {
		return false;
	}

	const signatureIndent = getLineIndent(signatureLine);

	for (let index = signatureLineOffset + 1; index < lines.length; index += 1) {
		const line = lines[index];
		const trimmedLine = line.trim();

		if (!trimmedLine || trimmedLine.startsWith('#')) {
			continue;
		}

		if (getLineIndent(line).length <= signatureIndent.length) {
			return false;
		}

		return trimmedLine.startsWith('"""') || trimmedLine.startsWith("'''");
	}

	return false;
}

function getIndentUnit(editor: vscode.TextEditor): string {
	if (editor.options.insertSpaces === false) {
		return '\t';
	}

	const tabSize = typeof editor.options.tabSize === 'number' ? editor.options.tabSize : 4;
	return ' '.repeat(tabSize);
}

function getLineIndent(line: string): string {
	return /^\s*/.exec(line)?.[0] ?? '';
}

function normalizeGeneratedDocstring(rawDocstring: string): string {
	let normalized = rawDocstring.trim();
	normalized = stripMarkdownFence(normalized);
	normalized = stripLeadingLanguageMarker(normalized);
	normalized = stripTripleQuoteWrapper(normalized);
	normalized = removeRemainingTripleQuotes(normalized);
	normalized = removeCommonIndent(normalized.trim());

	return normalized.trim();
}

function stripMarkdownFence(text: string): string {
	const lines = text.trim().split(/\r?\n/);

	if (lines.length >= 2 && lines[0].trim().startsWith('```')) {
		lines.shift();

		if (lines[lines.length - 1].trim().startsWith('```')) {
			lines.pop();
		}

		return lines.join('\n').trim();
	}

	return text.trim();
}

function stripLeadingLanguageMarker(text: string): string {
	const lines = text.trim().split(/\r?\n/);

	if (lines[0]?.trim().toLowerCase() === 'python') {
		return lines.slice(1).join('\n').trim();
	}

	return text.trim();
}

function stripTripleQuoteWrapper(text: string): string {
	const trimmed = text.trim();
	const quoteStyles = ['"""', "'''"];

	for (const quoteStyle of quoteStyles) {
		if (trimmed.startsWith(quoteStyle) && trimmed.endsWith(quoteStyle)) {
			return trimmed.slice(quoteStyle.length, -quoteStyle.length).trim();
		}
	}

	return trimmed;
}

function removeRemainingTripleQuotes(text: string): string {
	return text.replace(/"""/g, '').replace(/'''/g, '');
}

function removeCommonIndent(text: string): string {
	const lines = text.split(/\r?\n/);
	const indents = lines
		.filter((line) => line.trim())
		.map((line) => /^\s*/.exec(line)?.[0].length ?? 0);

	if (indents.length === 0) {
		return '';
	}

	const commonIndent = Math.min(...indents);

	if (commonIndent === 0) {
		return lines.join('\n');
	}

	return lines.map((line) => line.slice(commonIndent)).join('\n');
}

function formatDocstringForInsertion(docstringContent: string, bodyIndent: string): string {
	const lines = docstringContent.split(/\r?\n/).map((line) => line.trimEnd());

	if (lines.length === 1) {
		return `${bodyIndent}"""${lines[0]}"""\n`;
	}

	const [summary, ...rest] = lines;
	const formattedLines = [
		`${bodyIndent}"""${summary}`,
		...rest.map((line) => `${bodyIndent}${line}`),
		`${bodyIndent}"""`
	];

	return `${formattedLines.join('\n')}\n`;
}

function handleCommandError(prefix: string, error: unknown): void {
	const message = error instanceof Error ? error.message : String(error);
	const userMessage = error instanceof UserFacingError ? message : `${prefix} ${message}`;

	vscode.window.showErrorMessage(userMessage);
	log(`${prefix} ${message}`);
	logErrorDetails(error);
}

function logErrorDetails(error: unknown): void {
	if (error instanceof Error && error.stack) {
		log(error.stack);
		return;
	}

	log(String(error));
}

function log(message: string): void {
	if (outputChannel) {
		outputChannel.appendLine(message);
		return;
	}

	console.log(message);
}
