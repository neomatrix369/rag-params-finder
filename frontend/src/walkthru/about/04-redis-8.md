# Redis 8 as the vector store

Redis 8 ships the Query Engine, so it can store chunk embeddings and run vector search itself. Start a local Redis 8 container with one command and sweep against it:

```
./start-services.sh --redis-local
```

Redis is one of four vector stores the app supports, next to MongoDB Atlas, Postgres/pgvector and Elasticsearch. Each store is independent, so you can run the same configuration on each and compare **similarity scores**. The comparison is about scores, not speed; timings, where shown, are indicative only.
