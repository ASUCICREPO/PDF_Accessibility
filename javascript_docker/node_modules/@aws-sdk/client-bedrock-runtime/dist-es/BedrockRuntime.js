import { createAggregatedClient } from "@smithy/smithy-client";
import { BedrockRuntimeClient } from "./BedrockRuntimeClient";
import { ApplyGuardrailCommand, } from "./commands/ApplyGuardrailCommand";
import { ConverseCommand } from "./commands/ConverseCommand";
import { ConverseStreamCommand, } from "./commands/ConverseStreamCommand";
import { InvokeModelCommand } from "./commands/InvokeModelCommand";
import { InvokeModelWithResponseStreamCommand, } from "./commands/InvokeModelWithResponseStreamCommand";
const commands = {
    ApplyGuardrailCommand,
    ConverseCommand,
    ConverseStreamCommand,
    InvokeModelCommand,
    InvokeModelWithResponseStreamCommand,
};
export class BedrockRuntime extends BedrockRuntimeClient {
}
createAggregatedClient(commands, BedrockRuntime);
