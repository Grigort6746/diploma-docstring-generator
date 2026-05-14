import * as vscode from 'vscode';
import { execFile, spawn } from 'child_process';

const outputChannelName = 'Python Docstring Generator';
const generateDocstringCommand = 'python-docstring-generator.generateDocstring';
const checkOllamaConnectionCommand = 'python-docstring-generator.checkOllamaConnection';
const setupLocalEnvironmentCommand = 'python-docstring-generator.setupLocalEnvironment';
const regenerateDocstringCommand = 'python-docstring-generator.regenerateDocstring';
const showStatusMenuCommand = 'python-docstring-generator.showStatusMenu';
const refreshStatusCommand = 'python-docstring-generator.refreshStatus';
const showOutputCommand = 'python-docstring-generator.showOutput';
const ollamaInstallUrl = 'https://ollama.com/download';

let outputChannel: vscode.OutputChannel | undefined;
let statusBarItem: vscode.StatusBarItem | undefined;

interface ExtensionConfiguration {
	ollamaUrl: string;
	model: string;
	temperature: number;
	numPredict: number;
	autoStartOllama: boolean;
	autoPullModel: boolean;
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

interface OllamaPullResponse {
	status?: unknown;
	digest?: unknown;
	total?: unknown;
	completed?: unknown;
	error?: unknown;
}

type StatusBarState = 'unknown' | 'checking' | 'ready' | 'offline' | 'modelMissing' | 'starting' | 'downloading' | 'error';

type PreviewChoice = 'Insert' | 'Regenerate' | 'Cancel';

interface GenerateCommandOptions {
	isRegenerate?: boolean;
}

class UserFacingError extends Error {
	public constructor(message: string) {
		super(message);
		this.name = 'UserFacingError';
	}
}

class SetupChecklist {
	private readonly items: Array<{ label: string; status: 'pending' | 'ok' | 'failed'; detail?: string }> = [];

	public start(label: string, detail?: string): void {
		const existingItem = this.items.find((item) => item.label === label);

		if (existingItem) {
			existingItem.status = 'pending';
			existingItem.detail = detail;
			this.log();
			return;
		}

		this.items.push({ label, status: 'pending', detail });
		this.log();
	}

	public pass(label: string, detail?: string): void {
		this.set(label, 'ok', detail);
	}

	public fail(label: string, detail?: string): void {
		this.set(label, 'failed', detail);
	}

	public toDetail(): string {
		return this.items.map((item) => {
			const marker = item.status === 'ok' ? '[ok]' : item.status === 'failed' ? '[x]' : '[...]';
			return item.detail ? `${marker} ${item.label}: ${item.detail}` : `${marker} ${item.label}`;
		}).join('\n');
	}

	public logSummary(): void {
		log('Setup checklist summary:');
		log(this.toDetail());
	}

	private set(label: string, status: 'ok' | 'failed', detail?: string): void {
		const existingItem = this.items.find((item) => item.label === label);

		if (existingItem) {
			existingItem.status = status;
			existingItem.detail = detail;
			this.log();
			return;
		}

		this.items.push({ label, status, detail });
		this.log();
	}

	private log(): void {
		log(this.toDetail());
	}
}

class OllamaInstallRequiredError extends UserFacingError {
	public constructor() {
		super('Ollama is not installed or is not available in PATH. Install Ollama, then run setup again.');
		this.name = 'OllamaInstallRequiredError';
	}
}

class OllamaNotReachableError extends UserFacingError {
	public constructor() {
		super('Ollama is not reachable. Make sure it is running and the URL is correct.');
		this.name = 'OllamaNotReachableError';
	}
}

export function activate(context: vscode.ExtensionContext) {
	outputChannel = vscode.window.createOutputChannel(outputChannelName);
	statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
	statusBarItem.command = showStatusMenuCommand;
	statusBarItem.name = 'Python Docstring Generator';
	setStatusBarState('unknown');
	statusBarItem.show();

	const generateDisposable = vscode.commands.registerCommand(generateDocstringCommand, async () => {
		await runGenerateDocstringCommand();
	});

	const regenerateDisposable = vscode.commands.registerCommand(regenerateDocstringCommand, async () => {
		await runGenerateDocstringCommand({ isRegenerate: true });
	});

	const checkConnectionDisposable = vscode.commands.registerCommand(checkOllamaConnectionCommand, async () => {
		await runCheckOllamaConnectionCommand();
	});

	const setupDisposable = vscode.commands.registerCommand(setupLocalEnvironmentCommand, async () => {
		await runSetupLocalEnvironmentCommand();
	});

	const showStatusMenuDisposable = vscode.commands.registerCommand(showStatusMenuCommand, async () => {
		await showStatusMenu();
	});

	const refreshStatusDisposable = vscode.commands.registerCommand(refreshStatusCommand, async () => {
		await refreshStatusBar(false);
	});

	const showOutputDisposable = vscode.commands.registerCommand(showOutputCommand, () => {
		outputChannel?.show();
	});

	context.subscriptions.push(
		outputChannel,
		statusBarItem,
		generateDisposable,
		regenerateDisposable,
		checkConnectionDisposable,
		setupDisposable,
		showStatusMenuDisposable,
		refreshStatusDisposable,
		showOutputDisposable
	);

	log('Extension activated.');
	void refreshStatusBar(true);
}

export function deactivate() {
	outputChannel?.dispose();
	statusBarItem?.dispose();
}

function setStatusBarState(state: StatusBarState, detail?: string): void {
	if (!statusBarItem) {
		return;
	}

	const labels: Record<StatusBarState, string> = {
		unknown: '$(circle-large-outline) Docstring',
		checking: '$(sync~spin) Docstring: Checking',
		ready: '$(check) Docstring: Ready',
		offline: '$(plug) Docstring: Offline',
		modelMissing: '$(warning) Docstring: Model missing',
		starting: '$(debug-start) Docstring: Starting',
		downloading: '$(cloud-download) Docstring: Downloading',
		error: '$(error) Docstring: Error'
	};

	statusBarItem.text = labels[state];
	statusBarItem.tooltip = detail ? `Python Docstring Generator\n${detail}\nClick for actions.` : 'Python Docstring Generator\nClick for actions.';

	if (state === 'error') {
		statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
		return;
	}

	if (state === 'offline' || state === 'modelMissing') {
		statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
		return;
	}

	statusBarItem.backgroundColor = undefined;
}

async function refreshStatusBar(silent: boolean): Promise<void> {
	setStatusBarState('checking');

	try {
		const config = getConfiguration();
		const modelNames = await fetchOllamaModels(config);

		if (modelNames.includes(config.model)) {
			setStatusBarState('ready', `Model "${config.model}" is available at ${config.ollamaUrl}.`);

			if (!silent) {
				vscode.window.showInformationMessage(`Local model is ready: ${config.model}.`);
			}

			return;
		}

		setStatusBarState('modelMissing', `Model "${config.model}" is not installed.`);

		if (!silent) {
			const choice = await vscode.window.showWarningMessage(
				`Model "${config.model}" is not installed.`,
				'Setup Local Environment',
				'Show Output'
			);

			if (choice === 'Setup Local Environment') {
				await runSetupLocalEnvironmentCommand();
			}

			if (choice === 'Show Output') {
				outputChannel?.show();
			}
		}
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		setStatusBarState(error instanceof OllamaNotReachableError ? 'offline' : 'error', message);

		if (silent) {
			log(`Silent status refresh failed: ${message}`);
			return;
		}

		handleCommandError('Could not refresh local model status.', error);
	}
}

async function showStatusMenu(): Promise<void> {
	const picked = await vscode.window.showQuickPick(
		[
			{
				label: '$(edit) Generate Docstring',
				description: 'Generate, preview, then insert a docstring',
				action: generateDocstringCommand
			},
			{
				label: '$(refresh) Regenerate Docstring',
				description: 'Generate another candidate for the selected function',
				action: regenerateDocstringCommand
			},
			{
				label: '$(tools) Setup Local Environment',
				description: 'Start Ollama and download the configured model',
				action: setupLocalEnvironmentCommand
			},
			{
				label: '$(plug) Check Ollama Connection',
				description: 'Check server and model availability',
				action: checkOllamaConnectionCommand
			},
			{
				label: '$(sync) Refresh Status',
				description: 'Update the status bar indicator',
				action: refreshStatusCommand
			},
			{
				label: '$(output) Show Output Channel',
				description: 'Open technical diagnostics',
				action: showOutputCommand
			},
			{
				label: '$(settings-gear) Open Settings',
				description: 'Edit Python Docstring Generator settings',
				action: 'openSettings'
			}
		],
		{
			placeHolder: 'Python Docstring Generator actions'
		}
	);

	if (!picked) {
		return;
	}

	if (picked.action === 'openSettings') {
		await vscode.commands.executeCommand('workbench.action.openSettings', 'pythonDocstringGenerator');
		return;
	}

	await vscode.commands.executeCommand(picked.action);
}

async function runGenerateDocstringCommand(options: GenerateCommandOptions = {}): Promise<void> {
	log(options.isRegenerate ? 'Regenerate docstring command started.' : 'Generate docstring command started.');

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

		await vscode.window.withProgress(
			{
				location: vscode.ProgressLocation.Notification,
				title: 'Preparing local Ollama model...',
				cancellable: false
			},
			async (progress) => {
				await ensureLocalEnvironment(config, progress);
			}
		);

		let docstringContent = '';
		let attempt = 1;

		while (true) {
			docstringContent = await generateDocstringCandidate(config, prompt, attempt);

			const previewChoice = await showDocstringPreview(docstringContent, attempt);

			if (previewChoice === 'Insert') {
				break;
			}

			if (previewChoice === 'Regenerate') {
				attempt += 1;
				continue;
			}

			vscode.window.showInformationMessage('Docstring insertion cancelled.');
			log('Docstring insertion cancelled by user.');
			return;
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

		const successChoice = await vscode.window.showInformationMessage(
			'Python docstring generated and inserted.',
			'Regenerate',
			'Show Output'
		);

		if (successChoice === 'Regenerate') {
			await vscode.commands.executeCommand(regenerateDocstringCommand);
		}

		if (successChoice === 'Show Output') {
			outputChannel?.show();
		}

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
			async (progress) => getOllamaModelsWithAutoStart(config, progress)
		);

		if (modelNames.includes(config.model)) {
			vscode.window.showInformationMessage(`Ollama is running. Model "${config.model}" is available.`);
			return;
		}

		const choice = await vscode.window.showWarningMessage(
			`Model "${config.model}" is not installed or not available in Ollama.`,
			'Download Model',
			'Show Output'
		);

		if (choice === 'Download Model') {
			await runSetupLocalEnvironmentCommand();
			return;
		}

		if (choice === 'Show Output') {
			outputChannel?.show();
		}
	} catch (error) {
		handleCommandError('Could not connect to Ollama.', error);
	}
}

async function runSetupLocalEnvironmentCommand(): Promise<void> {
	log('Setup local environment command started.');
	const checklist = new SetupChecklist();
	checklist.pass('VS Code extension loaded');

	try {
		const config = getConfiguration();
		checklist.pass('Configuration valid', `Model "${config.model}" at ${config.ollamaUrl}`);

		await vscode.window.withProgress(
			{
				location: vscode.ProgressLocation.Notification,
				title: 'Setting up local docstring model...',
				cancellable: false
			},
			async (progress) => {
				await ensureLocalEnvironment(config, progress, { forcePullMissingModel: true, checklist });
			}
		);

		checklist.logSummary();

		const choice = await vscode.window.showInformationMessage(
			`Local environment is ready. Model "${config.model}" is available.`,
			{
				modal: true,
				detail: checklist.toDetail()
			},
			'Generate Docstring',
			'Show Output'
		);

		if (choice === 'Generate Docstring') {
			await vscode.commands.executeCommand(generateDocstringCommand);
		}

		if (choice === 'Show Output') {
			outputChannel?.show();
		}
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		checklist.fail('Local generation ready', message);
		checklist.logSummary();
		handleCommandError('Could not setup local environment.', error);
	}
}

function getConfiguration(): ExtensionConfiguration {
	const configuration = vscode.workspace.getConfiguration('pythonDocstringGenerator');
	const ollamaUrlValue = configuration.get<unknown>('ollamaUrl', 'http://localhost:11434');
	const modelValue = configuration.get<unknown>('model', 'qwen2.5-coder:1.5b');
	const temperatureValue = configuration.get<unknown>('temperature', 0.2);
	const numPredictValue = configuration.get<unknown>('numPredict', 256);
	const autoStartOllamaValue = configuration.get<unknown>('autoStartOllama', true);
	const autoPullModelValue = configuration.get<unknown>('autoPullModel', true);

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

	if (typeof autoStartOllamaValue !== 'boolean') {
		throw new UserFacingError('autoStartOllama must be true or false.');
	}

	if (typeof autoPullModelValue !== 'boolean') {
		throw new UserFacingError('autoPullModel must be true or false.');
	}

	return {
		ollamaUrl,
		model,
		temperature: temperatureValue,
		numPredict: numPredictValue,
		autoStartOllama: autoStartOllamaValue,
		autoPullModel: autoPullModelValue
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

async function generateDocstringCandidate(
	config: ExtensionConfiguration,
	prompt: string,
	attempt: number
): Promise<string> {
	const generatedText = await vscode.window.withProgress(
		{
			location: vscode.ProgressLocation.Notification,
			title: attempt === 1 ? 'Generating Python docstring...' : `Regenerating Python docstring (${attempt})...`,
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

	log(`Generated docstring candidate ${attempt}:`);
	log(docstringContent);

	return docstringContent;
}

async function showDocstringPreview(docstringContent: string, attempt: number): Promise<PreviewChoice> {
	while (true) {
		const choice = await vscode.window.showInformationMessage(
			attempt === 1 ? 'Generated docstring preview' : `Generated docstring preview (${attempt})`,
			{
				modal: true,
				detail: formatDocstringPreviewDetail(docstringContent)
			},
			'Insert',
			'Regenerate',
			'Cancel',
			'Show Output'
		);

		if (choice === 'Show Output') {
			outputChannel?.show();
			continue;
		}

		if (choice === 'Regenerate') {
			return 'Regenerate';
		}

		if (choice === 'Insert') {
			return 'Insert';
		}

		return 'Cancel';
	}
}

function formatDocstringPreviewDetail(docstringContent: string): string {
	return [
		'The generated docstring will be inserted into the selected function:',
		'',
		'"""',
		docstringContent,
		'"""'
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

async function ensureLocalEnvironment(
	config: ExtensionConfiguration,
	progress: vscode.Progress<{ message?: string; increment?: number }>,
	options: { forcePullMissingModel?: boolean; checklist?: SetupChecklist } = {}
): Promise<void> {
	setStatusBarState('checking', `Checking ${config.ollamaUrl}.`);
	progress.report({ message: 'Checking Ollama server...' });
	log(`Ensuring local environment for model "${config.model}".`);
	options.checklist?.start('Ollama API reachable', config.ollamaUrl);

	let modelNames = await getOllamaModelsWithAutoStart(config, progress, options.checklist);
	options.checklist?.pass('Ollama API reachable', config.ollamaUrl);
	options.checklist?.start('Model available', config.model);

	if (modelNames.includes(config.model)) {
		progress.report({ message: `Model "${config.model}" is already available.` });
		log(`Model "${config.model}" is already available.`);
		setStatusBarState('ready', `Model "${config.model}" is available.`);
		options.checklist?.pass('Model available', config.model);
		options.checklist?.pass('Local generation ready');
		return;
	}

	const shouldPull = options.forcePullMissingModel === true || config.autoPullModel;

	if (!shouldPull) {
		setStatusBarState('modelMissing', `Model "${config.model}" is not installed.`);
		options.checklist?.fail('Model available', `Model "${config.model}" is not installed.`);
		throw new UserFacingError(
			`Model "${config.model}" is not installed in Ollama. Enable autoPullModel or run setup.`
		);
	}

	setStatusBarState('downloading', `Downloading model "${config.model}".`);
	await pullOllamaModel(config, progress);
	modelNames = await fetchOllamaModels(config);

	if (!modelNames.includes(config.model)) {
		options.checklist?.fail('Model available', `Model "${config.model}" is not listed after download.`);
		throw new UserFacingError(`Model "${config.model}" was downloaded but is not listed by Ollama yet.`);
	}

	progress.report({ message: `Model "${config.model}" is ready.` });
	log(`Model "${config.model}" is ready.`);
	setStatusBarState('ready', `Model "${config.model}" is available.`);
	options.checklist?.pass('Model available', config.model);
	options.checklist?.pass('Local generation ready');
}

async function getOllamaModelsWithAutoStart(
	config: ExtensionConfiguration,
	progress: vscode.Progress<{ message?: string; increment?: number }>,
	checklist?: SetupChecklist
): Promise<string[]> {
	try {
		return await fetchOllamaModels(config);
	} catch (error) {
		if (!(error instanceof OllamaNotReachableError)) {
			throw error;
		}

		if (!config.autoStartOllama) {
			setStatusBarState('offline', 'Ollama is not reachable and autoStartOllama is disabled.');
			checklist?.fail('Ollama API reachable', 'Ollama is not reachable and autoStartOllama is disabled.');
			throw error;
		}

		if (!isLocalOllamaUrl(config.ollamaUrl)) {
			setStatusBarState('offline', 'Automatic start is supported only for localhost Ollama URLs.');
			checklist?.fail('Ollama API reachable', 'Automatic start is supported only for localhost Ollama URLs.');
			throw new UserFacingError(
				'Ollama is not reachable. Automatic start is supported only for localhost Ollama URLs.'
			);
		}

		setStatusBarState('starting', 'Trying to start local Ollama server.');
		checklist?.start('Ollama startup', 'ollama serve');
		progress.report({ message: 'Ollama is not running. Trying to start it...' });
		await startOllamaServer(checklist);
		await waitForOllama(config, progress);
		checklist?.pass('Ollama startup', 'ollama serve started');
		vscode.window.showInformationMessage('Ollama server started.');
		return fetchOllamaModels(config);
	}
}

async function startOllamaServer(checklist?: SetupChecklist): Promise<void> {
	checklist?.start('Ollama executable available', 'ollama');

	if (!(await isCommandAvailable('ollama'))) {
		setStatusBarState('offline', 'Ollama command was not found in PATH.');
		checklist?.fail('Ollama executable available', 'ollama was not found in PATH.');
		throw new OllamaInstallRequiredError();
	}

	checklist?.pass('Ollama executable available', 'ollama found in PATH.');
	log('Starting local Ollama server with "ollama serve".');

	const child = spawn('ollama', ['serve'], {
		detached: true,
		stdio: 'ignore',
		windowsHide: true
	});

	child.unref();
}

async function waitForOllama(
	config: ExtensionConfiguration,
	progress: vscode.Progress<{ message?: string; increment?: number }>
): Promise<void> {
	const attempts = 20;

	for (let attempt = 1; attempt <= attempts; attempt += 1) {
		progress.report({ message: `Waiting for Ollama to start (${attempt}/${attempts})...` });

		try {
			await fetchOllamaModels(config);
			return;
		} catch (error) {
			if (!(error instanceof OllamaNotReachableError)) {
				throw error;
			}

			await delay(1_000);
		}
	}

	throw new UserFacingError('Ollama did not start in time. Check the Output Channel for details.');
}

async function pullOllamaModel(
	config: ExtensionConfiguration,
	progress: vscode.Progress<{ message?: string; increment?: number }>
): Promise<void> {
	progress.report({ message: `Downloading model "${config.model}"...` });
	log(`Pulling Ollama model "${config.model}" via /api/pull.`);

	const endpoint = buildOllamaUrl(config.ollamaUrl, 'api/pull');
	const response = await fetchWithTimeout(endpoint, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			model: config.model,
			stream: true
		})
	}, 30 * 60_000);

	if (!response.ok) {
		const body = await readResponseText(response);
		log(`Ollama /api/pull returned HTTP ${response.status}.`);
		log(`Response body: ${body}`);
		throw new UserFacingError(formatOllamaHttpError(response.status, body, config.model));
	}

	await readOllamaPullStream(response, progress, config.model);
	vscode.window.showInformationMessage(`Model "${config.model}" downloaded and ready.`);
}

async function readOllamaPullStream(
	response: Response,
	progress: vscode.Progress<{ message?: string; increment?: number }>,
	model: string
): Promise<void> {
	if (!response.body) {
		throw new UserFacingError('Ollama did not return a model download stream.');
	}

	const reader = response.body.getReader();
	const decoder = new TextDecoder();
	let buffer = '';
	let lastPercent = 0;
	let lastStatus = '';

	while (true) {
		const { done, value } = await reader.read();

		if (done) {
			break;
		}

		buffer += decoder.decode(value, { stream: true });
		const lines = buffer.split(/\r?\n/);
		buffer = lines.pop() ?? '';

		for (const line of lines) {
			const update = parsePullStreamLine(line);

			if (!update) {
				continue;
			}

			if (typeof update.error === 'string' && update.error.trim()) {
				log(`Ollama /api/pull error field: ${update.error.trim()}`);
				throw new UserFacingError(formatOllamaErrorMessage(update.error.trim(), model));
			}

			const status = typeof update.status === 'string' ? update.status : '';

			if (status && status !== lastStatus) {
				lastStatus = status;
				log(`Model pull status: ${status}`);
				progress.report({ message: status });
			}

			if (typeof update.completed === 'number' && typeof update.total === 'number' && update.total > 0) {
				const percent = Math.floor((update.completed / update.total) * 100);
				const increment = Math.max(0, percent - lastPercent);
				lastPercent = percent;

				progress.report({
					message: `${status || 'Downloading'} ${percent}%`,
					increment
				});
			}

			if (status === 'success') {
				progress.report({ message: `Model "${model}" downloaded.`, increment: 100 - lastPercent });
				return;
			}
		}
	}

	if (buffer.trim()) {
		const update = parsePullStreamLine(buffer);

		if (typeof update?.error === 'string' && update.error.trim()) {
			throw new UserFacingError(formatOllamaErrorMessage(update.error.trim(), model));
		}

		if (update?.status === 'success') {
			return;
		}
	}
}

function parsePullStreamLine(line: string): OllamaPullResponse | undefined {
	const trimmedLine = line.trim();

	if (!trimmedLine) {
		return undefined;
	}

	try {
		return JSON.parse(trimmedLine) as OllamaPullResponse;
	} catch (error) {
		log(`Could not parse Ollama pull stream line: ${trimmedLine}`);
		logErrorDetails(error);
		return undefined;
	}
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

		throw new OllamaNotReachableError();
	} finally {
		clearTimeout(timeout);
	}
}

function buildOllamaUrl(baseUrl: string, endpoint: string): string {
	const normalizedBaseUrl = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
	return new URL(endpoint, normalizedBaseUrl).toString();
}

function isLocalOllamaUrl(value: string): boolean {
	try {
		const parsedUrl = new URL(value);
		return ['localhost', '127.0.0.1', '::1'].includes(parsedUrl.hostname);
	} catch {
		return false;
	}
}

async function isCommandAvailable(command: string): Promise<boolean> {
	const executable = process.platform === 'win32' ? 'where.exe' : 'which';

	try {
		await execFilePromise(executable, [command]);
		return true;
	} catch (error) {
		log(`Command "${command}" was not found in PATH.`);
		logErrorDetails(error);
		return false;
	}
}

function execFilePromise(command: string, args: string[]): Promise<void> {
	return new Promise((resolve, reject) => {
		execFile(command, args, { windowsHide: true }, (error) => {
			if (error) {
				reject(error);
				return;
			}

			resolve();
		});
	});
}

function delay(ms: number): Promise<void> {
	return new Promise((resolve) => {
		setTimeout(resolve, ms);
	});
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

	if (error instanceof OllamaInstallRequiredError || error instanceof OllamaNotReachableError) {
		setStatusBarState('offline', message);
	} else {
		setStatusBarState('error', message);
	}

	if (error instanceof OllamaInstallRequiredError) {
		vscode.window.showErrorMessage(userMessage, 'Open Ollama Download', 'Show Output').then(async (choice) => {
			if (choice === 'Open Ollama Download') {
				await vscode.env.openExternal(vscode.Uri.parse(ollamaInstallUrl));
			}

			if (choice === 'Show Output') {
				outputChannel?.show();
			}
		});
	} else {
		vscode.window.showErrorMessage(userMessage, 'Show Output').then((choice) => {
			if (choice === 'Show Output') {
				outputChannel?.show();
			}
		});
	}

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
