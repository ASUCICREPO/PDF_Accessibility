import {
  AwsSdkSigV4AuthInputConfig,
  AwsSdkSigV4AuthResolvedConfig,
  AwsSdkSigV4PreviouslyResolved,
} from "@aws-sdk/core";
import {
  HandlerExecutionContext,
  HttpAuthScheme,
  HttpAuthSchemeParameters,
  HttpAuthSchemeParametersProvider,
  HttpAuthSchemeProvider,
} from "@smithy/types";
import { BedrockRuntimeClientResolvedConfig } from "../BedrockRuntimeClient";
export interface BedrockRuntimeHttpAuthSchemeParameters
  extends HttpAuthSchemeParameters {
  region?: string;
}
export interface BedrockRuntimeHttpAuthSchemeParametersProvider
  extends HttpAuthSchemeParametersProvider<
    BedrockRuntimeClientResolvedConfig,
    HandlerExecutionContext,
    BedrockRuntimeHttpAuthSchemeParameters,
    object
  > {}
export declare const defaultBedrockRuntimeHttpAuthSchemeParametersProvider: (
  config: BedrockRuntimeClientResolvedConfig,
  context: HandlerExecutionContext,
  input: object
) => Promise<BedrockRuntimeHttpAuthSchemeParameters>;
export interface BedrockRuntimeHttpAuthSchemeProvider
  extends HttpAuthSchemeProvider<BedrockRuntimeHttpAuthSchemeParameters> {}
export declare const defaultBedrockRuntimeHttpAuthSchemeProvider: BedrockRuntimeHttpAuthSchemeProvider;
export interface HttpAuthSchemeInputConfig extends AwsSdkSigV4AuthInputConfig {
  httpAuthSchemes?: HttpAuthScheme[];
  httpAuthSchemeProvider?: BedrockRuntimeHttpAuthSchemeProvider;
}
export interface HttpAuthSchemeResolvedConfig
  extends AwsSdkSigV4AuthResolvedConfig {
  readonly httpAuthSchemes: HttpAuthScheme[];
  readonly httpAuthSchemeProvider: BedrockRuntimeHttpAuthSchemeProvider;
}
export declare const resolveHttpAuthSchemeConfig: <T>(
  config: T & HttpAuthSchemeInputConfig & AwsSdkSigV4PreviouslyResolved
) => T & HttpAuthSchemeResolvedConfig;
