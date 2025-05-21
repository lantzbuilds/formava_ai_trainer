## TODO
- [] is sync_hevy page necessary, or should fetch auto in bkgrd?
- [] folder name: prepopulate text input, but editable
- [] double dates on Plan (folder) title
- [] add update functionality to Profile page
- [] implement Routines page
- [] add more split options to AI Recs page
- [] implement TBD sections on Dashboard
- in routine generation need to:
    [] seed more workout history
    [?] vectorize workout history and give to gpt
    [] test if gpt is basing new routines on history
    [?] make gpt assign weights to sets when appropriate
        why null->Bodyweight for Bicep Curl?
    [?] Why single sets on Leg day for ppl?
    [?] Make sure all routines have appropriate # sets
- [] weight conversions: store all weights in kg, but add imperial/metric pref for profile and convert
- [] test that routines are saved in CouchDB
- [] Available equip: update Register, UserProf model (and db views?) to include
- [] add langsmith for RAG telemetry observability?
- [] add single-step agentic reflection to RAG flow?
    - [] score response for relevance, groundedness, correctness
    - [] increases latency and token count (premium?)
- [] monetization: what features could be premium?
    - [] how do you fence features, check payment (Stripe token?)
- [] check different models for response quality
- [] handle failed validations on Register more gracefully

