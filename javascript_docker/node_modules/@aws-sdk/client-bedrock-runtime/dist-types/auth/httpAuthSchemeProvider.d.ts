import { AwsSdkSigV4AuthInputConfig, AwsSdkSigV4AuthResolvedConfig, AwsSdkSigV4PreviouslyResolved } from "@aws-sdk/core";
import { HandlerExecutionContext, HttpAuthScheme, HttpAuthSchemeParameters, HttpAuthSchemeParametersProvider, HttpAuthSchemeProvider } from "@smithy/types";
import { BedrockRuntimeClientResolvedConfig } from "../BedrockRuntimeClient";
/**
 * @internal
 */
export interface BedrockRuntimeHttpAuthSchemeParameters extends HttpAuthSchemeParameters {
    region?: string;
}
/**
 * @internal
 */
export interface BedrockRuntimeHttpAuthSchemeParametersProvider extends HttpAuthSchemeParametersProvider<BedrockRuntimeClientResolvedConfig, HandlerExecutionContext, BedrockRuntimeHttpAuthSchemeParameters, object> {
}
/**
 * @internal
 */
export declare const defaultBedrockRuntimeHttpAuthSchemeParametersProvider: (config: BedrockRuntimeClientResolvedConfig, context: HandlerExecutionContext, input: object) => Promise<BedrockRuntimeHttpAuthSchemeParameters>;
/**
 * @internal
 */
export interface BedrockRuntimeHttpAuthSchemeProvider extends HttpAuthSchemeProvider<BedrockRuntimeHttpAuthSchemeParameters> {
}
/**
 * @internal
 */
export declare const defaultBedrockRuntimeHttpAuthSchemeProvider: BedrockRuntimeHttpAuthSchemeProvider;
/**
 * @internal
 */
export interface HttpAuthSchemeInputConfig extends AwsSdkSigV4AuthInputConfig {
    /**
     * Configuration of HttpAuthSchemes for a client which provides default identity providers and signers per auth scheme.
     * @internal
     */
    httpAuthSchemes?: HttpAuthScheme[];
    /**
     * Configuration of an HttpAuthSchemeProvider for a client which resolves which HttpAuthScheme to use.
     * @internal
     */
    httpAuthSchemeProvider?: BedrockRuntimeHttpAuthSchemeProvider;
}
/**
 * @internal
 */
export interface HttpAuthSchemeResolvedConfig extends AwsSdkSigV4AuthResolvedConfig {
    /**
     * Configuration of HttpAuthSchemes for a client which provides default identity providers and signers per auth scheme.
     * @internal
     */
    readonly httpAuthSchemes: HttpAuthScheme[];
    /**
     * Configuration of an HttpAuthSchemeProvider for a client which resolves which HttpAuthScheme to use.
     * @internal
     */
    readonly httpAuthSchemeProvider: BedrockRuntimeHttpAuthSchemeProvider;
}
/**
 * @internal
 */
export declare const resolveHttpAuthSchemeConfig: <T>(config: T & HttpAuthSchemeInputConfig & AwsSdkSigV4PreviouslyResolved) => T & HttpAuthSchemeResolvedConfig;
