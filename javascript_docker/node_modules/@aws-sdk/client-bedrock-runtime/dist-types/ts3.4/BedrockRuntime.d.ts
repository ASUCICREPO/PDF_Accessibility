import { HttpHandlerOptions as __HttpHandlerOptions } from "@smithy/types";
import { BedrockRuntimeClient } from "./BedrockRuntimeClient";
import {
  ApplyGuardrailCommandInput,
  ApplyGuardrailCommandOutput,
} from "./commands/ApplyGuardrailCommand";
import {
  ConverseCommandInput,
  ConverseCommandOutput,
} from "./commands/ConverseCommand";
import {
  ConverseStreamCommandInput,
  ConverseStreamCommandOutput,
} from "./commands/ConverseStreamCommand";
import {
  InvokeModelCommandInput,
  InvokeModelCommandOutput,
} from "./commands/InvokeModelCommand";
import {
  InvokeModelWithResponseStreamCommandInput,
  InvokeModelWithResponseStreamCommandOutput,
} from "./commands/InvokeModelWithResponseStreamCommand";
export interface BedrockRuntime {
  applyGuardrail(
    args: ApplyGuardrailCommandInput,
    options?: __HttpHandlerOptions
  ): Promise<ApplyGuardrailCommandOutput>;
  applyGuardrail(
    args: ApplyGuardrailCommandInput,
    cb: (err: any, data?: ApplyGuardrailCommandOutput) => void
  ): void;
  applyGuardrail(
    args: ApplyGuardrailCommandInput,
    options: __HttpHandlerOptions,
    cb: (err: any, data?: ApplyGuardrailCommandOutput) => void
  ): void;
  converse(
    args: ConverseCommandInput,
    options?: __HttpHandlerOptions
  ): Promise<ConverseCommandOutput>;
  converse(
    args: ConverseCommandInput,
    cb: (err: any, data?: ConverseCommandOutput) => void
  ): void;
  converse(
    args: ConverseCommandInput,
    options: __HttpHandlerOptions,
    cb: (err: any, data?: ConverseCommandOutput) => void
  ): void;
  converseStream(
    args: ConverseStreamCommandInput,
    options?: __HttpHandlerOptions
  ): Promise<ConverseStreamCommandOutput>;
  converseStream(
    args: ConverseStreamCommandInput,
    cb: (err: any, data?: ConverseStreamCommandOutput) => void
  ): void;
  converseStream(
    args: ConverseStreamCommandInput,
    options: __HttpHandlerOptions,
    cb: (err: any, data?: ConverseStreamCommandOutput) => void
  ): void;
  invokeModel(
    args: InvokeModelCommandInput,
    options?: __HttpHandlerOptions
  ): Promise<InvokeModelCommandOutput>;
  invokeModel(
    args: InvokeModelCommandInput,
    cb: (err: any, data?: InvokeModelCommandOutput) => void
  ): void;
  invokeModel(
    args: InvokeModelCommandInput,
    options: __HttpHandlerOptions,
    cb: (err: any, data?: InvokeModelCommandOutput) => void
  ): void;
  invokeModelWithResponseStream(
    args: InvokeModelWithResponseStreamCommandInput,
    options?: __HttpHandlerOptions
  ): Promise<InvokeModelWithResponseStreamCommandOutput>;
  invokeModelWithResponseStream(
    args: InvokeModelWithResponseStreamCommandInput,
    cb: (err: any, data?: InvokeModelWithResponseStreamCommandOutput) => void
  ): void;
  invokeModelWithResponseStream(
    args: InvokeModelWithResponseStreamCommandInput,
    options: __HttpHandlerOptions,
    cb: (err: any, data?: InvokeModelWithResponseStreamCommandOutput) => void
  ): void;
}
export declare class BedrockRuntime
  extends BedrockRuntimeClient
  implements BedrockRuntime {}
