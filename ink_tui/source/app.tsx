import React, { useState, useEffect, useRef } from 'react';
import { Text, Box, useStdout } from 'ink';
import { spawn, ChildProcessWithoutNullStreams } from 'child_process';
import path from "path";
import TextInput from 'ink-text-input';
import readline from 'readline';
import Spinner from './spinner.js';
import gradient from 'gradient-string'

const ENTER_ALT_SCREEN = '\x1b[?1049h';
const LEAVE_ALT_SCREEN = '\x1b[?1049l';

const statusColor = {
	ok: 'cyan',
	inprocess: 'blue',
	done: 'green',
	warning: 'yellow',
	error: 'red',
}

type Message = {
	'type': 'agent' | 'user' | 'error',
	'message_id':string,
	'message': string
}

export default function App() {
	const [input, setInput] = useState('');
	const [history, setHistory] = useState<Message[]>([{
		type: 'agent',
		message_id: 'init',
		message: "Hello! How can I help you today?"
	}]);
	const [isTyping, setIsTyping] = useState(false);
	const { stdout } = useStdout();
	const [agentReady, setAgentReady] = useState(false);
	const [setupMessages, setSetupMessages] = useState<Record<string, {
		message: string,
		status: "inprocess" | "done" | "error" | "ok" | "warning"
	}>>({});

	const [size, setSize] = useState({
		columns: stdout.columns || 80,
		rows: stdout.rows || 24,
	});

	useEffect(() => {
		const handleResize = () => {
			setSize({
				columns: stdout.columns || 80,
				rows: stdout.rows || 24,
			});
		};

		stdout.on('resize', handleResize);
		return () => {
			stdout.off('resize', handleResize);
		};
	}, [stdout]);

	// Keep a persistent reference to the background Python process
	const pyProcess = useRef<ChildProcessWithoutNullStreams | null>(null);

	useEffect(() => {
		pyProcess.current = spawn(path.join(process.cwd(), '.venv', 'bin', 'python'), ['-u', 'agent.py']);

		const rl = readline.createInterface({
			input: pyProcess.current.stdout,
			terminal: false
		});

		rl.on('line', (line) => {
			try {
				const response = JSON.parse(line.trim());
				setHistory((prev) => ([
						...prev,
						{
							type: 'agent',
							message: response.message,
							message_id: response.message_id
						}
					]))

				if (response.status === "ok" && response.id === "agent_ready") {
					setAgentReady(true);
					setSetupMessages(prev => ({ ...prev, [response.id]: response }));
				}
				else if (response.status === "ok" && response.id === "stream_chunk") {
					setHistory((prev) => ([
						...prev,
						{
							type: 'agent',
							message: response.message,
							message_id: response.message_id
						}
					]))
				} else if (response.status === "error" && response.id === "disaster") {
					setHistory((prev) => ([
						...prev,
						{
							type: 'error',
							message: response.error,
							message_id: `error-id-${String(crypto.randomUUID())}`
						}
					]))
				} else {
					setSetupMessages(prev => ({ ...prev, [response.id]: response }));
				}
			} catch (err) {
				setHistory(prev => [...prev, {
					type: 'error',
					message: `Raw Output: ${line}`,
					message_id: `error-id-${String(crypto.randomUUID())}`
				}]);
			}
			setIsTyping(false);
		});

		pyProcess.current.stderr.on('data', (data) => {
			setSetupMessages(prev => ({
				...prev,
				"py_crash": { message: `PYTHON ERROR: ${data.toString()}`, status: "error" }
			}));
		});

		// FIX 3: Catch Spawn Errors (e.g., ENOENT missing virtual env)
		pyProcess.current.on('error', (err) => {
			setSetupMessages(prev => ({
				...prev,
				"sys_error": { message: `SPAWN ERROR: ${err.message}`, status: "error" }
			}));
		});

		// FIX 4: Catch Premature Exits
		pyProcess.current.on('close', (code) => {
			if (code !== 0) {
				setSetupMessages(prev => ({
					...prev,
					"sys_close": { message: `Process exited with code ${code}`, status: "error" }
				}));
			}
		});

		return () => {
			pyProcess.current?.kill();
		};
	}, []);

	const handleSubmit = (value: string) => {
		if (!value.trim() || isTyping) return;
		const uuid = crypto.randomUUID();
		setHistory(prev => [...prev, {
			type: 'user',
			message: value,
			message_id: String(uuid)
		}]);
		setIsTyping(true);
		setInput('');

		const payload = JSON.stringify({ message: value, message_id: String(uuid) });
		pyProcess.current?.stdin.write(payload + '\n');
	};

	return (
		<Box
			flexDirection="column"
			padding={1}
			width={size.columns}
			height={size.rows}
			borderStyle="single"
			borderColor="dim"
		>
			<Box marginBottom={1} flexDirection='column'>
				<Text color="magenta">
					{gradient(['#4895dd', '#be667e'])('█▀▀ █▀█ ▄▀█ █▀▀ █▀▀ █▄░█ ▀█▀')}
				</Text>
				<Text color="magenta">
					{gradient(['#4895dd', '#be667e'])('█▄▄ █▀▄ █▀█ █▄█ ██▄ █░▀█ ░█░')}
				</Text>
				<Text>{'─'.repeat(size.columns - 4)}</Text>
			</Box>
			{
				!agentReady ? (
					<Box flexDirection='row'>
						<Text color="whiteBright">
							{`Initialising `}
						</Text>
						<Spinner color="whiteBright" />
					</Box>
				) : null
			}
			<Box flexDirection='column' justifyContent="space-between" flexGrow={1}>
				{
					agentReady ? (
						<Box flexDirection="column" marginBottom={1}>
							<Text color="red">
								Messages: {history.length}
							</Text>
							{history.map((msg, index) => (
								<Box flexDirection='row'>
									{
										msg.type == "agent" ?
											(
												<Box marginRight={2} marginBottom={1}>
													<Text
														color="whiteBright"
														backgroundColor="#164e63"
													>
														{" Agent "}
													</Text>
												</Box>
											) :
											msg.type == "user" ? (
												<Box marginRight={2} marginBottom={1}>
													<Text
														color="whiteBright"
														backgroundColor="#14532d"
													>
														{" User "}
													</Text>
												</Box>
											) : (
												<Box marginRight={2} marginBottom={1}>
													<Text
														color="whiteBright"
														backgroundColor="#7f1d1d"
													>
														{" Error "}
													</Text>
												</Box>

											)
									}
									<Text key={index} color={msg.type == "agent" ? 'green' : 'white'}>
										{msg.message}
									</Text>
									{/* {
								bot is thinking
							} */}
								</Box>
							))}
							{isTyping && <Text color="yellow" dimColor>Bot is thinking...</Text>}
						</Box>
					) : (
						Object.keys(setupMessages).length > 0 ? (
							<Box flexDirection="column"
								borderStyle="single"
								borderColor="dim">
								{Object.entries(setupMessages).map(([id, msgDetails]) => (
									<Box flexDirection="row">
										<Text key={id} color={statusColor[msgDetails.status]}>
											{msgDetails.message}
										</Text>
										{
											msgDetails.status == "inprocess" ? (
												<Spinner color={statusColor['inprocess']} />
											) : null
										}
									</Box>

								))}
							</Box>
						) : null
					)
				}
				{
					agentReady ? (
						<Box>
							<Text bold color="cyan">➔ </Text>
							<TextInput
								value={input}
								onChange={setInput}
								onSubmit={handleSubmit}
								placeholder="Type a message and press Enter..."
							/>
						</Box>
					) : null
				}
			</Box>
		</Box>
	);
}

process.stdout.write(ENTER_ALT_SCREEN);

process.on('exit', () => {
	process.stdout.write(LEAVE_ALT_SCREEN);
});