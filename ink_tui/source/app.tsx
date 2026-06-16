import React, { useState, useEffect, useRef } from 'react';
import { Text, Box, useStdout } from 'ink';
import { spawn, ChildProcessWithoutNullStreams } from 'child_process';
import path from "path";
import TextInput from 'ink-text-input';

const ENTER_ALT_SCREEN = '\x1b[?1049h';
const LEAVE_ALT_SCREEN = '\x1b[?1049l';

const status_color = {
	'ok': 'green',
	'inprocess': 'blue',
	'done': 'green',
	'warning': 'yellow',
	'error': 'red',
}

export default function App() {
	const [input, setInput] = useState('');
	const [history, setHistory] = useState<string[]>(['Bot: Hello! How can I help you today?']);
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
		// The "-u" flag forces Python's stdout to be completely unbuffered
		pyProcess.current = spawn(path.join(process.cwd(), '.venv', 'bin', 'python'), ['-u', 'agent.py']);

		// Listen to incoming data chunks from the Python script
		pyProcess.current.stdout.on('data', (data) => {
			try {
				const response = JSON.parse(data.toString().trim());
				setSetupMessages(prev => ({ ...prev, [response.id]: response }));
				if (response.status == "ok" && response.id == "agent_ready") {
					setAgentReady(true)
				}
			} catch (err) {
				setHistory(prev => [...prev, `Raw Output: ${data.toString()}\nerror: ${err}`]);
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

		setHistory(prev => [...prev, `You: ${value}`]);
		setIsTyping(true);
		setInput('');

		const payload = JSON.stringify({ message: value });
		pyProcess.current?.stdin.write(payload + '\n');
	};

	return (
		<Box
			flexDirection="column"
			padding={1}
			width={size.columns}
			height={size.rows}
			justifyContent="space-between"
			borderStyle="single"
			borderColor="dim"
		>

			{
				agentReady ? (
					<Box flexDirection="column" marginBottom={1}>
						{history.map((msg, index) => (
							<Text key={index} color={msg.startsWith('You:') ? 'green' : 'white'}>
								{msg}
							</Text>

						))}
						{isTyping && <Text color="yellow" dimColor>Bot is thinking...</Text>}
					</Box>
				) : (
					<Box flexDirection="column"
						borderStyle="single"
						borderColor="dim">
						<Text>
							{setSetupMessages.length}
						</Text>
						{Object.entries(setupMessages).map(([id, msgDetails]) => (
							<Text key={id} color={status_color[msgDetails.status]}>
								{msgDetails.message}
							</Text>

						))}
					</Box>
				)
			}
			{/* {
				agentReady ? (
					
				) : null
			} */}
			<Box>
				<Text bold color="cyan">➔ </Text>
				<TextInput
					value={input}
					onChange={setInput}
					onSubmit={handleSubmit}
					placeholder="Type a message and press Enter..."
				/>
			</Box>
		</Box>
	);
}

process.stdout.write(ENTER_ALT_SCREEN);

process.on('exit', () => {
	process.stdout.write(LEAVE_ALT_SCREEN);
});