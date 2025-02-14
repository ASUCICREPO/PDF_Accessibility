# Troubleshooting CDK Issue: CannotPullContainerError & Docker Push Failure

## Issue

When running Fargate tasks, encountering the following error:

```json
"StoppedReason": "CannotPullContainerError: ref pull has been retried 1 time(s): failed to unpack image on snapshotter overlayfs: failed to extract layer sha256:c02342326b04a05fa0fc4c703c4aaa8ffb46cc0f2eda269c4a0dee53c8296182: failed to get stream processor for application/vnd.in-toto+json: no processor for media-type: unknown"
```

Additionally, checking the AWS Web UI:
- The ECR image referenced by the task definition has **0 size**.
- The `CannotPullContainerError` will be visible in ECS task logs.

### CDK Deployment Error:

When running `cdk deploy`, the following error occurs:

```sh
fail: docker push to ecr unexpected status from PUT request 400 Bad Request
```

- The `400 Bad Request` error occurs during `cdk deploy`.
- Sometimes, even with this error, the images may still be present in ECR. **Cross-check ECR to ensure images have valid sizes.**

## Potential Fixes

### 1. Update AWS CDK
Ensure you are using the latest version of AWS CDK:
```sh
npm install -g aws-cdk
```
Then, try redeploying:
```sh
cdk deploy
```

### 2. Delete `cdk.out` Folder & Remove Stale ECR Assets
1. Delete the `cdk.out` folder:
   ```sh
   rm -rf cdk.out
   ```
2. Go to AWS ECR (Elastic Container Registry) and manually delete the images that were pushed earlier.
3. Re-run `cdk deploy`.

### 3. Ensure Image is Properly Built and Pushed
If the image size in ECR is `0.0`, try the following:
- Open `docker_autotag.py`, add an empty space or a newline, then save the file.
- Do the same for your `alt-text.js`.
- Re-run `cdk deploy` to force rebuilding and pushing the images.

### 4. Verify ECR Image Sizes
- Check that the image sizes in ECR are **not** `0.0`.
- Typical image sizes for a functional ECS task should be approximately **150MB for autotag and 500MB for alt-text**.

### 5. Try All Variations
If issues persist, retry the above steps in different orders:
1. Update CDK
2. Delete `cdk.out` & ECR assets
3. Modify `docker_autotag.py` & `alt-text.js`
4. Ensure images are properly built and pushed

## Expected Outcome
- If `cdk deploy` passes, verify that image sizes are **not** `0.0` in ECR.
- If the image sizes are valid in ECR, the ECS task should run successfully.
- `CannotPullContainerError` would no longer appear in ECS task logs.
- If `cdk deploy` still throws a `400 Bad Request`, cross-check ECR as images may still be correctly pushed.

## Resolution Update (14 Feb 2025)
This issue has been referenced in the following GitHub issues:
- [aws/aws-cdk#30258](https://github.com/aws/aws-cdk/issues/30258)
- [aws/aws-cdk#33264](https://github.com/aws/aws-cdk/issues/33264)

This issue has been fixed and will be available in an upcoming CDK package release soon.

