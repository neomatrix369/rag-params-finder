# How it works

You write one YAML file that lists the options you want to compare. Three pieces do the rest:

- **CLI** - submits your sweep to the server.
- **Server** - for every combination, reads your PDF, splits it into chunks, embeds them, stores them in a vector database and searches with your questions.
- **Dashboard** - shows every run, the best settings and the retrieved chunks.

A sweep embeds and searches only. It makes no LLM answer-generation calls, so it stays cheap to repeat. Results are **similarity scores**: how close a retrieved chunk is to a question in embedding space.

A guided Walkthru of the dashboard is planned for this demo.
