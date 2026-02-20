Motivation

Question to anwer: how we structure the data so that the agent can answer our question better if they only have a code base
- what it means to be better


# 1. qualitative
Use natrual language to asks information about the workflow, how much the agent know about the workflow already with just:
- understanding the workflow repo vs. 
- a claude detailed summary in natural language vs.
- the token of understanding the workflow from template_WRD.yaml

How transferable is the template_WRD.yml
- compare it with a claude detailed summary

# 2. qualitative
compare token of understanding the workflow repo vs. 
- a claude detailed summary in natural language
- the token of understanding the workflow from template_WRD.yaml

How transferable is the template_WRD.yml
- compare it with a claude detailed summary

# further down
If you have 200gb of I/O, those information being feed into agent is also huge.
If you have many hardware options in the system, what is a better way for agent 

use claude project to come up with workflow question prompt:
1. agent interception from Jaime's github
2. claude code hooks (pre tool use)
    - get all the info that claude what file it has accessed, token, context

GraphRAG (Graph Retrieval-Augmented Generation) is an advanced AI framework developed by Microsoft that enhances Retrieval-Augmented Generation (RAG) by using knowledge graphs to improve LLM reasoning over complex, private, or disconnected data.

Jaime's tool: paper to MD -> feed all my old papers to WIDGET claude project