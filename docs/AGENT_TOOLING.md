# Agent tooling choices

The optional ReviewGate adapter uses OpenAI's Python Agents SDK with a typed output schema. The [official agent guide](https://openai.github.io/openai-agents-python/agents/) documents `Agent`, tools, model configuration and `output_type`; its structured output can use Pydantic models. Structured shape does not guarantee factual accuracy.

The [official human-in-the-loop guide](https://openai.github.io/openai-agents-python/human_in_the_loop/) documents `needs_approval`, paused `interruptions`, and approval/rejection before resuming. This prototype intentionally has no outbound action tools at all. The application stores model drafts in pending status and requires a separate local approval tied to the exact text hash before export. That local CLI approval is not the SDK's authenticated production approval service.

The model is selected explicitly at execution time instead of hardcoding an unverified claim about the latest or best model. Check the provider's current model catalogue, availability, costs and data handling before enabling live requests. No model key is stored in this repository, and no real model request is required by the core demo or offline tests.

Model tracing should be disabled for this sensitive-workflow prototype. Review every input before enabling any network call. Regex masking is not an information-security boundary: names, account numbers, confidential business facts and many other fields can survive masking. Use synthetic inputs until the privacy, security and contractual controls required for real client work exist.

A bounded run reduces runaway interactions but is not a monetary budget. The outer coordinator must enforce spending authorization and provider-level limits before any live model evaluation. SDK imports or mocked tests prove neither live provider compatibility nor useful draft quality.
