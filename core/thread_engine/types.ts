export interface ChatMessage {
  role: "system" | "user" | "assistant"
  content: string
}

export type LLMCompleter = (messages: ChatMessage[]) => Promise<string>
