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

	if (hasExistingDocstring(editor.document, signatureDocumentLine)) {
		vscode.window.showWarningMessage('The selected function already appears to contain a docstring.');
		return;
	}

	const config = getConfiguration();
	const prompt = generatePrompt(selectedCode.trim());

	log('Selected Python code:');
	log(selectedCode);
	log(`Using Ollama model "${config.model}" at ${config.ollamaUrl}.`);

	try {
		const generatedText = await vscode.window.withProgress(
			{
				location: vscode.ProgressLocation.Notification,
				title: 'Generating Python docstring...',
				cancellable: false
			},
			async () => callOllama(config, prompt)
		);

		const docstringContent = normalizeGeneratedDocstring(generatedText);

		if (!docstringContent) {
			throw new Error('The model returned an empty docstring.');
		}

		const signatureIndent = getLineIndent(editor.document.lineAt(signatureDocumentLine).text) || signature.indent;
		const bodyIndent = signatureIndent + getIndentUnit(editor);
		const insertionText = formatDocstringForInsertion(docstringContent, bodyIndent);
		const insertionPosition = new vscode.Position(signatureDocumentLine + 1, 0);

		await editor.edit((editBuilder) => {
			editBuilder.insert(insertionPosition, insertionText);
		});

		vscode.window.showInformationMessage('Python docstring generated and inserted.');
		log('Generated docstring:');
		log(docstringContent);
	} catch (error) {
		handleCommandError('Failed to generate Python docstring.', error);
	}
}

async function runCheckOllamaConnectionCommand(): Promise<void> {
	const config = getConfiguration();

	try {
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
			`Ollama is running, but model "${config.model}" was not found. Install it or choose another model in settings.`
		);
	} catch (error) {
		handleCommandError('Could not connect to Ollama.', error);
	}
}

function getConfiguration(): ExtensionConfiguration {
	const configuration = vscode.workspace.getConfiguration('pythonDocstringGenerator');

	return {
		ollamaUrl: configuration.get<string>('ollamaUrl', 'http://localhost:11434').trim(),
		model: configuration.get<string>('model', 'qwen2.5-coder:1.5b').trim(),
		temperature: configuration.get<number>('temperature', 0.2),
		numPredict: configuration.get<number>('numPredict', 256)
	};
}

function generatePrompt(code: string): string {
	return [
		'Generate a Google-style Python docstring for the following function.',
		'',
		'Requirements:',
		'- Return only the docstring.',
		'- Do not include Markdown.',
		'- Do not repeat the code.',
		'- Document all arguments.',
		'- Include Returns if the function returns a value.',
		'- Include Raises only if the function clearly raises exceptions.',
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

	if (!response.ok) {
		const body = await readResponseText(response);
		throw new Error(formatOllamaHttpError(response.status, body, config.model));
	}

	const data = await response.json() as OllamaGenerateResponse;

	if (typeof data.error === 'string' && data.error.trim()) {
		throw new Error(`Ollama returned an error: ${data.error.trim()}`);
	}

	if (typeof data.response !== 'string' || !data.response.trim()) {
		throw new Error('Ollama returned an empty response.');
	}

	return data.response;
}

async function fetchOllamaModels(config: ExtensionConfiguration): Promise<string[]> {
	const endpoint = buildOllamaUrl(config.ollamaUrl, 'api/tags');
	const response = await fetchWithTimeout(endpoint, {
		method: 'GET'
	}, 10_000);

	if (!response.ok) {
		const body = await readResponseText(response);
		throw new Error(formatOllamaHttpError(response.status, body, config.model));
	}

	const data = await response.json() as OllamaTagsResponse;
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
		if (error instanceof Error && error.name === 'AbortError') {
			throw new Error(`Request to Ollama timed out after ${Math.round(timeoutMs / 1000)} seconds.`);
		}

		throw new Error('Ollama is not reachable. Make sure the local Ollama server is running.');
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
		return `Ollama returned 404. Check that model "${model}" is installed.`;
	}

	if (trimmedBody) {
		return `Ollama returned HTTP ${status}: ${trimmedBody}`;
	}

	return `Ollama returned HTTP ${status}.`;
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

function hasExistingDocstring(document: vscode.TextDocument, signatureLine: number): boolean {
	const nextLine = signatureLine + 1;

	if (nextLine >= document.lineCount) {
		return false;
	}

	const nextText = document.lineAt(nextLine).text.trimStart();
	return nextText.startsWith('"""') || nextText.startsWith("'''");
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
	normalized = stripTripleQuoteWrapper(normalized);
	normalized = removeCommonIndent(normalized.trim());

	return normalized.trim();
}

function stripMarkdownFence(text: string): string {
	const lines = text.split(/\r?\n/);

	if (lines.length >= 2 && lines[0].trim().startsWith('```') && lines[lines.length - 1].trim() === '```') {
		return lines.slice(1, -1).join('\n').trim();
	}

	return text;
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
	vscode.window.showErrorMessage(`${prefix} ${message}`);

	log(`${prefix} ${message}`);

	if (error instanceof Error && error.stack) {
		log(error.stack);
	}
}

function log(message: string): void {
	if (outputChannel) {
		outputChannel.appendLine(message);
		return;
	}

	console.log(message);
}
