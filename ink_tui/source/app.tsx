import React, { useState, useEffect, useRef } from 'react';
import { Text, Box, useStdout, useInput, useApp } from 'ink';
import { spawn, ChildProcessWithoutNullStreams } from 'child_process';
import path from "path";
import TextInput from 'ink-text-input';
import readline from 'readline';
import Spinner from './spinner.js';
import gradient from 'gradient-string'
import { ScrollView, ScrollViewRef } from "ink-scroll-view";

const ENTER_ALT_SCREEN = '\x1b[?1049h';
const LEAVE_ALT_SCREEN = '\x1b[?1049l';

const statusColor = {
	ok: 'cyan',
	inprocess: 'blue',
	done: 'green',
	warning: 'yellow',
	error: 'red',
}
const chatIcon = {
	'agent': '👾',
	'user': '❱ ',
	'error': '💥',
}
const chatMsgColor = {
	'agent': 'white',
	'user': '#fb923c',
	'error': '#7f1d1d',
}

type Message = {
	'type': 'agent' | 'user' | 'error',
	'message_id': string,
	'message': string
}

export default function App() {
	const scrollRef = useRef<ScrollViewRef>(null);
	const { exit } = useApp()
	const [userScrolledUp, setUserScrolledUp] = useState(false);
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

	const headerHeight = 4;
	const inputHeight = 3;
	const borderAndPadding = 4;
	const messagesWrapperMargin = 1;
	const scrollHeight = Math.max(
		1,
		size.rows - headerHeight - inputHeight - borderAndPadding - messagesWrapperMargin
	);

	useEffect(() => {
		const handleResize = () => {
			setSize({
				columns: stdout.columns || 80,
				rows: stdout.rows || 24,
			});
			scrollRef.current?.remeasure();
		};

		stdout.on('resize', handleResize);
		return () => {
			stdout.off('resize', handleResize);
		};
	}, [stdout]);

	useInput((_, key) => {
		if (key.upArrow) {
			scrollRef.current?.scrollBy(-1);
			setUserScrolledUp(true);
		}
		if (key.downArrow) {
			scrollRef.current?.scrollBy(1);
			const offset = scrollRef.current?.getScrollOffset() ?? 0;
			const bottom = scrollRef.current?.getBottomOffset() ?? 0;
			if (offset >= bottom) setUserScrolledUp(false);
		}
		if (key.pageUp) {
			const height = scrollRef.current?.getViewportHeight() || 1;
			scrollRef.current?.scrollBy(-height);
			setUserScrolledUp(true);
		}
		if (key.pageDown) {
			const height = scrollRef.current?.getViewportHeight() || 1;
			scrollRef.current?.scrollBy(height);
			const offset = scrollRef.current?.getScrollOffset() ?? 0;
			const bottom = scrollRef.current?.getBottomOffset() ?? 0;
			if (offset >= bottom) setUserScrolledUp(false);
		}
	});

	useEffect(() => {
		if (!userScrolledUp && scrollRef.current) {
			setTimeout(() => scrollRef.current?.scrollToBottom(), 0);
		}
	}, [history, isTyping, userScrolledUp]);

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

				if (response.status === "ok" && response.id === "agent_ready") {
					setAgentReady(true);
					setSetupMessages(prev => ({ ...prev, [response.id]: response }));
				}
				else if (response.status === "ok" && response.id === "stream_chunk") {
					setHistory((prev) => {
						const chat = prev.find(chatmsg => chatmsg.type == "agent" && chatmsg.message_id == response.message_id)
						if (chat) {
							chat.message = chat.message.concat(response.message)
							return [...prev]
						} else {
							return [
								...prev,
								{
									type: 'agent',
									message: response.message,
									message_id: response.message_id
								}
							]
						}
					})
				} else if (response.status === "error" && response.id === "disaster") {
					setHistory((prev) => ([
						...prev,
						{
							type: 'error',
							message: response.error,
							message_id: `error-id-${String(crypto.randomUUID())}`
						}
					]))
					setSetupMessages(prev => ({ ...prev, [response.id]: response }));
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
		if (value.trim() == "clear") {
			setHistory([])
			return
		}
		else if (["quit", "exit"].includes(value.trim())) {
			pyProcess.current?.kill();
			exit()
			return
		}
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
			<Box marginBottom={1} flexDirection='column' flexShrink={0}>
				<Text color="magenta">
					{gradient(['#4895dd', '#be667e'])('█▀▀ █▀█ ▄▀█ █▀▀ █▀▀ █▄░█ ▀█▀')}
				</Text>
				<Text color="magenta">
					{gradient(['#4895dd', '#be667e'])('█▄▄ █▀▄ █▀█ █▄█ ██▄ █░▀█ ░█░')}
				</Text>
				<Text color="#737373">{'─'.repeat(size.columns - 4)}</Text>
			</Box>
			{
				!agentReady ? (
					<Box flexDirection='row' marginBottom={1}>
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
						<Box flexDirection="column" marginBottom={1} flexGrow={1}>
							<Box height={scrollHeight} flexShrink={0}>
								<ScrollView ref={scrollRef}>
									{history.map((msg, index) => (
										<Box flexDirection='row'
										{
										...(
											msg.type == "user" ? {
												marginBottom:0
											} : {
												marginBottom:1
											}
										)
										}
										>
											{
												msg.type == "agent" ?
													(
														<Box marginRight={2} marginBottom={1}>
															<Text
																color={chatMsgColor['agent']}
															>
																{chatIcon['agent']}
															</Text>
														</Box>
													) :
													msg.type == "user" ? (
														<Box
															marginRight={2}
															marginBottom={1}
														>
															<Text
																color={chatMsgColor['user']}
															>
																{chatIcon['user']}
															</Text>
														</Box>
													) : (
														<Box marginRight={2} marginBottom={1}>
															<Text
																color={chatMsgColor['error']}
															>
																{chatIcon['error']}
															</Text>
														</Box>
													)
											}
											<Text key={index} color={chatMsgColor[msg.type]}>
												{msg.message}
											</Text>
										</Box>
									))}
								</ScrollView>
							</Box>

							{isTyping && (
								<Box>
									<Text color="yellow" dimColor>{`Agent is thinking `}</Text>
									<Spinner color="whiteBright" />
								</Box>
							)}
						</Box>
					) : (
						Object.keys(setupMessages).length > 0 ? (
							<Box flexDirection="column">
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
						<Box backgroundColor={"#262626"} padding={1}>
							<Text bold color={chatMsgColor['user']}>{chatIcon['user']}</Text>
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