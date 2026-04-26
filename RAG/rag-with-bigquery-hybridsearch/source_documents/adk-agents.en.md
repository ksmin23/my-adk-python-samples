# ADK Agents

ADK Agents are the core components for building autonomous applications within the Agent Development Kit. They are designed to be modular and can be combined to create complex systems.

## Core Concepts

- **BaseAgent Class:** The fundamental class that all other agents extend from. It provides the basic structure and lifecycle for an agent.
- **Orchestration:** Agents can be orchestrated to run in sequence, in parallel, or in loops, allowing for the creation of sophisticated workflows.

## Types of Agents

- **LLM Agents:** These agents leverage Large Language Models (LLMs) like Gemini to understand natural language, reason, and make decisions. They are the primary agents for interacting with users and data.
- **Workflow Agents:** These agents act as controllers, managing the execution flow of other agents. They enable you to build complex, multi-step processes.
- **Custom Agents:** You can create your own agents by extending the `BaseAgent` class. This allows for the implementation of unique logic and integrations tailored to specific needs.
