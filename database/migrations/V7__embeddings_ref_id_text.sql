-- EcoForge AI :: V7 - embeddings.ref_id must be TEXT, not UUID.
--
-- The retriever identifies an intervention by its SLUG ("rooftop-solar-pv"),
-- which is the stable business key used everywhere else in the engine and in
-- the API. V4 declared ref_id as UUID, which no caller ever produces, so the
-- very first upsert failed with:
--     invalid input syntax for type uuid: "rooftop-solar-pv"
--
-- The UNIQUE (collection, ref_type, ref_id, chunk_index) constraint and the
-- collection index both survive the type change.
ALTER TABLE embeddings
    ALTER COLUMN ref_id TYPE TEXT USING ref_id::text;