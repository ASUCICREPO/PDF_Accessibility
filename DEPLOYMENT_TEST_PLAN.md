# Enhanced Deployment Script Test Plan

## Overview
This document outlines the comprehensive test plan for the enhanced `deploy-unified-enhanced.sh` script that implements cascading deployment for PDF Accessibility solutions.

## Key Features Implemented

### 1. **Cascading Deployment Logic**
- ✅ Deploy first solution (PDF-to-PDF OR PDF-to-HTML)
- ✅ Offer to deploy second solution after first completes
- ✅ Offer UI deployment after backend(s) complete
- ✅ Smart bucket management for single vs dual deployments

### 2. **Enhanced Error Handling**
- ✅ Comprehensive validation at each step
- ✅ Graceful fallbacks for bucket name detection
- ✅ Proper cleanup of temporary directories
- ✅ Detailed error messages with troubleshooting guidance

### 3. **Smart Bucket Management**
- ✅ Multiple methods for PDF-to-PDF bucket detection
- ✅ Automatic bucket configuration for UI deployment
- ✅ Support for single-bucket and dual-bucket scenarios

### 4. **UI Integration**
- ✅ Automatic UI repository cloning
- ✅ Environment variable configuration
- ✅ Amplify URL extraction and display
- ✅ Proper cleanup after deployment

## Test Scenarios

### Scenario 1: PDF-to-PDF → UI
```bash
./deploy-unified-enhanced.sh
# Choose: 1 (PDF-to-PDF)
# After deployment: Choose 2 (Deploy UI)
# Expected: Single bucket used for both UI configurations
```

### Scenario 2: PDF-to-HTML → UI  
```bash
./deploy-unified-enhanced.sh
# Choose: 2 (PDF-to-HTML)
# After deployment: Choose 2 (Deploy UI)
# Expected: Single bucket used for both UI configurations
```

### Scenario 3: PDF-to-PDF → PDF-to-HTML → UI
```bash
./deploy-unified-enhanced.sh
# Choose: 1 (PDF-to-PDF)
# After deployment: Choose 1 (Deploy other solution)
# After second deployment: Choose Y (Deploy UI)
# Expected: Both buckets configured in UI
```

### Scenario 4: PDF-to-HTML → PDF-to-PDF → UI
```bash
./deploy-unified-enhanced.sh
# Choose: 2 (PDF-to-HTML)
# After deployment: Choose 1 (Deploy other solution)
# After second deployment: Choose Y (Deploy UI)
# Expected: Both buckets configured in UI
```

### Scenario 5: Backend Only (No UI)
```bash
./deploy-unified-enhanced.sh
# Choose: 1 or 2 (Any backend)
# After deployment: Choose 3 (Finish)
# Expected: Clean exit with backend summary
```

## Critical Validations

### 1. **Environment Variables**
- ✅ AWS credentials validation
- ✅ Required parameters collection
- ✅ Proper variable scoping between functions

### 2. **Bucket Name Detection**
- ✅ CloudFormation stack outputs (primary method)
- ✅ S3 API listing with time-based filtering (fallback)
- ✅ Pattern-based bucket discovery (final fallback)
- ✅ Graceful handling of detection failures

### 3. **UI Repository Integration**
- ✅ Successful repository cloning
- ✅ Branch validation (pdf2html)
- ✅ Script execution permissions
- ✅ Environment variable passing

### 4. **Error Recovery**
- ✅ Build failure handling with logs
- ✅ Network connectivity issues
- ✅ Permission errors
- ✅ Resource conflicts

## Pre-Deployment Checklist

### AWS Prerequisites
- [ ] AWS CLI configured with appropriate permissions
- [ ] US East 1 region selected
- [ ] Bedrock NOVA models enabled (NOVA-PRO for PDF-to-PDF, NOVA-Lite for PDF-to-HTML)
- [ ] Adobe PDF Services API credentials (for PDF-to-PDF)

### Script Prerequisites  
- [ ] Script has execute permissions (`chmod +x deploy-unified-enhanced.sh`)
- [ ] Internet connectivity for repository cloning
- [ ] Sufficient disk space for temporary files
- [ ] `jq` utility available for JSON parsing

## Expected Outputs

### Successful Single Backend Deployment
```
🎊 Deployment Complete!
=======================

📊 Deployment Summary:
   ✅ PDF-to-PDF Remediation: pdfaccessibility-bucket-xyz123
   
🔍 Monitor builds in AWS Console:
   https://console.aws.amazon.com/codesuite/codebuild/projects

🚀 Your PDF accessibility solution is ready to use!
```

### Successful Full Stack Deployment
```
🎊 Deployment Complete!
=======================

📊 Deployment Summary:
   ✅ PDF-to-PDF Remediation: pdfaccessibility-bucket-xyz123
   ✅ PDF-to-HTML Remediation: pdf2html-bucket-123456789-us-east-1
   🌐 Frontend UI: https://main.d1234567890.amplifyapp.com

🔍 Monitor builds in AWS Console:
   https://console.aws.amazon.com/codesuite/codebuild/projects

🚀 Your PDF accessibility solution is ready to use!
```

## Risk Mitigation

### 1. **Bucket Name Detection Failure**
- **Risk**: PDF-to-PDF bucket name not detected
- **Mitigation**: Multiple detection methods with clear user guidance
- **Fallback**: Manual bucket identification instructions

### 2. **UI Deployment Failure**
- **Risk**: UI repository access or deployment issues
- **Mitigation**: Comprehensive error handling with cleanup
- **Fallback**: Backend remains functional, UI can be deployed separately

### 3. **Resource Conflicts**
- **Risk**: CodeBuild project name conflicts
- **Mitigation**: Unique project naming with solution suffixes
- **Fallback**: Graceful handling of existing resources

### 4. **Network Issues**
- **Risk**: Repository cloning or AWS API failures
- **Mitigation**: Clear error messages with retry suggestions
- **Fallback**: Manual deployment instructions

## Success Criteria

### ✅ Functional Requirements
- [x] Deploy PDF-to-PDF solution independently
- [x] Deploy PDF-to-HTML solution independently  
- [x] Deploy both solutions in sequence
- [x] Deploy UI with proper bucket configuration
- [x] Handle all user choice combinations

### ✅ Non-Functional Requirements
- [x] Clear user interface with progress indicators
- [x] Comprehensive error handling and recovery
- [x] Proper resource cleanup
- [x] Secure credential handling
- [x] Detailed logging and troubleshooting information

## Deployment Command

```bash
cd /Users/shaashvatmittal/Desktop/PDF_Accessibility
./deploy-unified-enhanced.sh
```

## Post-Deployment Verification

### Backend Verification
1. Check CloudFormation stacks in AWS Console
2. Verify S3 buckets created with proper structure
3. Test file upload to appropriate bucket folders
4. Monitor processing through CloudWatch (PDF-to-PDF) or Lambda logs (PDF-to-HTML)

### UI Verification  
1. Access Amplify URL provided in deployment output
2. Test user registration and authentication
3. Verify file upload functionality
4. Confirm processing status monitoring
5. Test file download after processing

## Troubleshooting Guide

### Common Issues
1. **"Failed to get AWS account ID"** → Check AWS CLI configuration
2. **"Failed to create BDA project"** → Verify Bedrock permissions
3. **"Could not detect bucket name"** → Check CloudFormation console manually
4. **"UI deployment failed"** → Check internet connectivity and repository access

### Debug Commands
```bash
# Check AWS configuration
aws sts get-caller-identity

# List CloudFormation stacks
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE

# List S3 buckets
aws s3 ls

# Check CodeBuild projects
aws codebuild list-projects
```

This enhanced deployment script provides a robust, user-friendly experience for deploying the complete PDF Accessibility solution stack with intelligent cascading options and comprehensive error handling.
