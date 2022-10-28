# data-dota

# Questions for the project

- At what day time/season/month matches happen? 
- At what day time/season/month people stamp or comeback? (data from the dota api) 
- Spike in win-rate by champion/season/month?
- Which lineup/other champions favors certain champions?

# Whats gonna be done project?

The pipeline has to have these areas: ingestion of (raw) data, staging zone for cleaned and enriched data, and a curated zone for production data analytics.

The zones need to be connected by a data pipelines using Apache Airflow.

## Pipeline 1
- Brings raw data to landing zone. Brings data from the source to a transient storage

> Questions
> Like mongo db?
> This data is ephemeral?

## Pipeline 2

Moves data from landing zone to staging.}
- Clean data
- Wrangle/transform the data
- Enrich the data (merge multiple datasets into a single one)
- Persist data

## Pipeline 3+
Moves from staging to production, trigger the update of data marts (views). This pipeline perform some additional transformation and feed the data systems of choice (SQL and Neo4j) for populate the analysis.

- Launch the queries (SQL/Cypher)
- SQL database should follow the star schema principles
- Persist data

> Questions
> The views get the data systems in production stage?
> Airflow triggers the update of the views?

# Some ideas

Usage of start schema nad graph schema: parallel schemas with two different purposes 

1. Start schema for day light dimension to compare for frequency of comeback and stamp and peak of heroes

2. Graph schema for topography (movie examples)


# Graph schema
Which lineup/other champions favors certain champions?
Give the champions where the match was win
```
cham 1
cham 2 win

cham1 
chan3 lose

cham 1
cham 2 win
```

## Proposals
champ -IN (win) -> match (timestamp properties)

champ -IN-> lineup -PLAYS (win)-> match(timestamp properties)

# Questions

Use Shapely to match the cities to region is enrichment or just transformation?

# Project Submission Checklist
- [ ] repository with the code, well documented, including
- [ ] docker-compose file to run the environment
- [ ] detailed description of the various steps
- [ ] report (Can be in the Repository README) with the project 
- [ ] design steps (divided per area)
- [ ] Example dataset: the project testing should work offline, i.e., you need to have some sample data points.
slides for the project presentation.

### Extra

- [ ] launching docker containers via airflow to schedule job
- [ ] STAR schema design includes maintenance upon updates
- [ ] using REDIS for speeding up steps
- [ ] creativity: data viz, serious analysis, performance analysis, extensive cleansing
