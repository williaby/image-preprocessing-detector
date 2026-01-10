@echo off
REM Create tarballs for Stage 2 training dataset using tar from WSL

cd /d E:\image_detection\03_training_datasets\stage2_diqa_ensemble

echo Creating train tarball...
wsl tar -czf tarballs/stage2_train.tar.gz splits/train.jsonl checksums/train_checksums.sha256 images/diqa-5000/train images/smartdoc-qa/train images/funsd/train images/sroie/train images/tobacco-800/train

echo Creating val tarball...
wsl tar -czf tarballs/stage2_val.tar.gz splits/val.jsonl checksums/val_checksums.sha256 images/diqa-5000/val images/smartdoc-qa/val images/funsd/val images/sroie/val images/tobacco-800/val

echo Creating test tarball...
wsl tar -czf tarballs/stage2_test.tar.gz splits/test.jsonl checksums/test_checksums.sha256 images/diqa-5000/test images/smartdoc-qa/test images/funsd/test images/sroie/test images/tobacco-800/test

echo Creating metadata tarball...
wsl tar -czf tarballs/stage2_metadata.tar.gz README.md MANIFEST.json

echo Done! Listing tarballs:
dir tarballs\*.tar.gz
