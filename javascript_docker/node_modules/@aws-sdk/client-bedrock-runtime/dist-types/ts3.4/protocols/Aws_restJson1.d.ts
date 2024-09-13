import {
  HttpRequest as __HttpRequest,
  HttpResponse as __HttpResponse,
} from "@smithy/protocol-http";
import {
  EventStreamSerdeContext as __EventStreamSerdeContext,
  SerdeContext as __SerdeContext,
} from "@smithy/types";
import {
  ApplyGuardrailCommandInput,
  ApplyGuardrailCommandOutput,
} from "../commands/ApplyGuardrailCommand";
import {
  ConverseCommandInput,
  ConverseCommandOutput,
} from "../commands/ConverseCommand";
import {
  ConverseStreamCommandInput,
  ConverseStreamCommandOutput,
} from "../commands/ConverseStreamCommand";
import {
  InvokeModelCommandInput,
  InvokeModelCommandOutput,
} from "../commands/InvokeModelCommand";
import {
  InvokeModelWithResponseStreamCommandInput,
  InvokeModelWithResponseStreamCommandOutput,
} from "../commands/InvokeModelWithResponseStreamCommand";
export declare const se_ApplyGuardrailCommand: (
  input: ApplyGuardrailCommandInput,
  context: __SerdeContext
) => Promise<__HttpRequest>;
export declare const se_ConverseCommand: (
  input: ConverseCommandInput,
  context: __SerdeContext
) => Promise<__HttpRequest>;
export declare const se_ConverseStreamCommand: (
  input: ConverseStreamCommandInput,
  context: __SerdeContext
) => Promise<__HttpRequest>;
export declare const se_InvokeModelCommand: (
  input: InvokeModelCommandInput,
  context: __SerdeContext
) => Promise<__HttpRequest>;
export declare const se_InvokeModelWithResponseStreamCommand: (
  input: InvokeModelWithResponseStreamCommandInput,
  context: __SerdeContext
) => Promise<__HttpRequest>;
export declare const de_ApplyGuardrailCommand: (
  output: __HttpResponse,
  context: __SerdeContext
) => Promise<ApplyGuardrailCommandOutput>;
export declare const de_ConverseCommand: (
  output: __HttpResponse,
  context: __SerdeContext
) => Promise<ConverseCommandOutput>;
export declare const de_ConverseStreamCommand: (
  output: __HttpResponse,
  context: __SerdeContext & __EventStreamSerdeContext
) => Promise<ConverseStreamCommandOutput>;
export declare const de_InvokeModelCommand: (
  output: __HttpResponse,
  context: __SerdeContext
) => Promise<InvokeModelCommandOutput>;
export declare const de_InvokeModelWithResponseStreamCommand: (
  output: __HttpResponse,
  context: __SerdeContext & __EventStreamSerdeContext
) => Promise<InvokeModelWithResponseStreamCommandOutput>;
