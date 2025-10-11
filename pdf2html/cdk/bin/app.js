#!/usr/bin/env node

const { App } = require('aws-cdk-lib');
const { Pdf2HtmlStack } = require('../lib/pdf2html-stack');

const app = new App();

// Ensure region is set - fail if not provided
const region = process.env.CDK_DEFAULT_REGION;
const account = process.env.CDK_DEFAULT_ACCOUNT;

if (!region) {
  console.error('❌ CDK_DEFAULT_REGION environment variable is required');
  process.exit(1);
}

if (!account) {
  console.error('❌ CDK_DEFAULT_ACCOUNT environment variable is required');
  process.exit(1);
}

console.log(`🚀 Deploying PDF-to-HTML stack to region: ${region}`);

new Pdf2HtmlStack(app, 'Pdf2HtmlStack', {
  env: { 
    account: account, 
    region: region
  },
  description: 'PDF to HTML Accessibility Utility on AWS'
});
