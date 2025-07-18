#!/usr/bin/env node

const { App } = require('aws-cdk-lib');
const { Pdf2HtmlStack } = require('../lib/pdf2html-stack');

const app = new App();
new Pdf2HtmlStack(app, 'Pdf2HtmlStack', {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1'
  },
  description: 'PDF to HTML Accessibility Utility on AWS'
});
