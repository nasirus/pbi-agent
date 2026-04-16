# TODO

- [x] Replay ChatGPT tool calls together with their outputs on follow-up requests
- [x] Add regression coverage for the ChatGPT tool follow-up shape
- [x] Replay ChatGPT turn-state headers within a turn and clear them after completion
- [x] Reuse raw backend function-call items for ChatGPT tool follow-ups
- [x] Retry ChatGPT tool follow-ups once without previous_response_id after invalid_request_error
- [x] Include current-turn replay history when the ChatGPT fallback drops previous_response_id
- [x] Run targeted validation and append session memory
