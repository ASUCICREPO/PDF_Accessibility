import { HttpRequest as __HttpRequest, HttpResponse as __HttpResponse } from "@smithy/protocol-http";
import { EventStreamSerdeContext as __EventStreamSerdeContext, SerdeContext as __SerdeContext } from "@smithy/types";
import { ApplyGuardrailCommandInput, ApplyGuardrailCommandOutput } from "../commands/ApplyGuardrailCommand";
import { ConverseCommandInput, ConverseCommandOutput } from "../commands/ConverseCommand";
import { ConverseStreamCommandInput, ConverseStreamCommandOutput } from "../commands/ConverseStreamCommand";
import { InvokeModelCommandInput, InvokeModelCommandOutput } from "../commands/InvokeModelCommand";
import { InvokeModelWithResponseStreamCommandInput, InvokeModelWithResponseStreamCommandOutput } from "../commands/InvokeModelWithResponseStreamCommand";
/**
 * serializeAws_restJson1ApplyGuardrailCommand
 */
export declare const se_ApplyGuardrailCommand: (input: ApplyGuardrailCommandInput, context: __SerdeContext) => Promise<__HttpRequest>;
/**
 * serializeAws_restJson1ConverseCommand
 */
export declare const se_ConverseCommand: (input: ConverseCommandInput, context: __SerdeContext) => Promise<__HttpRequest>;
/**
 * serializeAws_restJson1ConverseStreamCommand
 */
export declare const se_ConverseStreamCommand: (input: ConverseStreamCommandInput, context: __SerdeContext) => Promise<__HttpRequest>;
/**
 * serializeAws_restJson1InvokeModelCommand
 */
export declare const se_InvokeModelCommand: (input: InvokeModelCommandInput, context: __SerdeContext) => Promise<__HttpRequest>;
/**
 * serializeAws_restJson1InvokeModelWithResponseStreamCommand
 */
export declare const se_InvokeModelWithResponseStreamCommand: (input: InvokeModelWithResponseStreamCommandInput, context: __SerdeContext) => Promise<__HttpRequest>;
/**
 * deserializeAws_restJson1ApplyGuardrailCommand
 */
export declare const de_ApplyGuardrailCommand: (output: __HttpResponse, context: __SerdeContext) => Promise<ApplyGuardrailCommandOutput>;
/**
 * deserializeAws_restJson1ConverseCommand
 */
export declare const de_ConverseCommand: (output: __HttpResponse, context: __SerdeContext) => Promise<ConverseCommandOutput>;
/**
 * deserializeAws_restJson1ConverseStreamCommand
 */
export declare const de_ConverseStreamCommand: (output: __HttpResponse, context: __SerdeContext & __EventStreamSerdeContext) => Promise<ConverseStreamCommandOutput>;
/**
 * deserializeAws_restJson1InvokeModelCommand
 */
export declare const de_InvokeModelCommand: (output: __HttpResponse, context: __SerdeContext) => Promise<InvokeModelCommandOutput>;
/**
 * deserializeAws_restJson1InvokeModelWithResponseStreamCommand
 */
export declare const de_InvokeModelWithResponseStreamCommand: (output: __HttpResponse, context: __SerdeContext & __EventStreamSerdeContext) => Promise<InvokeModelWithResponseStreamCommandOutput>;
