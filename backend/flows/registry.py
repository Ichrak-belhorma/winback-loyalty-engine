from flows.steps import FlowDefinition

FLOWS: dict[str, FlowDefinition] = {}


def register(definition: FlowDefinition) -> FlowDefinition:
    FLOWS[definition.name] = definition
    return definition
