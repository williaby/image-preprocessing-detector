# GitHub Repository Setup Instructions

**Status**: Repository configured locally, ready for GitHub creation and push
**Date**: 2025-11-05

---

## Current Status

✅ **Completed**:
- Git remote configured: `https://github.com/williaby/image-preprocessing-detector.git`
- All security and community files committed locally
- Commit created: `feat: add OpenSSF Scorecard and Contributor Covenant badge infrastructure`
- Pre-commit hooks passed successfully

⏳ **Pending**:
- GitHub repository creation (must be done via GitHub UI or CLI)
- Initial push to GitHub
- Branch protection configuration
- GitHub Apps configuration

---

## Step 1: Create GitHub Repository

### Option A: Via GitHub Web UI (Recommended)

1. **Navigate to**: https://github.com/new
2. **Repository Details**:
   - **Owner**: `williaby`
   - **Repository name**: `image-preprocessing-detector`
   - **Description**: `Intelligent image preprocessing detection system for RAG applications`
   - **Visibility**: ✅ **Public** (required for OpenSSF Scorecard badge)
3. **Initialization**:
   - ❌ **DO NOT** add README (already exists locally)
   - ❌ **DO NOT** add .gitignore (already exists locally)
   - ❌ **DO NOT** add license (LICENSE file already exists locally)
4. **Click**: "Create repository"

### Option B: Via GitHub CLI (Alternative)

```bash
# Create public repository
gh repo create williaby/image-preprocessing-detector \
  --public \
  --description "Intelligent image preprocessing detection system for RAG applications" \
  --source=. \
  --remote=origin \
  --push
```

**Note**: If using GitHub CLI, skip Step 2 below (it will push automatically).

---

## Step 2: Push Code to GitHub

After creating the repository via Web UI:

```bash
# Verify remote is configured
git remote -v
# Should show:
# origin	https://github.com/williaby/image-preprocessing-detector.git (fetch)
# origin	https://github.com/williaby/image-preprocessing-detector.git (push)

# Push to GitHub
git push -u origin main

# Verify push succeeded
git log --oneline -1
# Should show: 378d6e4 feat: add OpenSSF Scorecard and Contributor Covenant badge infrastructure
```

**Expected Output**:
```
Enumerating objects: XX, done.
Counting objects: 100% (XX/XX), done.
Delta compression using up to X threads
Compressing objects: 100% (XX/XX), done.
Writing objects: 100% (XX/XX), XX.XX KiB | XX.XX MiB/s, done.
Total XX (delta XX), reused XX (delta XX), pack-reused 0
remote: Resolving deltas: 100% (XX/XX), done.
To https://github.com/williaby/image-preprocessing-detector.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

---

## Step 3: Enable Branch Protection

**Navigate to**: https://github.com/williaby/image-preprocessing-detector/settings/branches

### Branch Protection Rules for `main`

Click "Add branch protection rule" and configure:

#### General Settings
- **Branch name pattern**: `main`

#### Protect Matching Branches
✅ **Require a pull request before merging**
  - ✅ Require approvals: **0** (solo developer - cannot approve own PRs)
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ✅ Require review from Code Owners

✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - **Required status checks** (add after first workflow runs):
    - `CI Success Gate`
    - `CI Gate`
    - `Security Gate Validation`
    - `Scorecard Analysis`

✅ **Require conversation resolution before merging**

✅ **Require signed commits**

✅ **Require linear history**

✅ **Require deployments to succeed before merging** (optional, skip for now)

#### Do Not Allow Bypassing
✅ **Do not allow bypassing the above settings**

#### Rules Applied to Everyone
✅ **Restrict who can push to matching branches**
  - **Allowed**: Maintainers only (you)

✅ **Block force pushes**

✅ **Allow deletions**: ❌ **Uncheck this** (prevent branch deletion)

Click **"Create"** to save the branch protection rule.

---

## Step 4: Configure GitHub Apps

### Required Apps (Free Tier)

#### 1. Renovate Bot
**Purpose**: Automated dependency updates with smart security prioritization

**Setup**:
1. Install from: https://github.com/apps/renovate
2. Grant access to `image-preprocessing-detector` repository
3. Configuration already present in `renovate.json`
4. First run will create dependency dashboard issue

**Expected Behavior**:
- Weekly dependency update PRs
- Immediate security vulnerability PRs
- Auto-merge for GitHub Actions minor/patch updates
- Manual review required for image processing libraries

#### 2. Codecov
**Purpose**: Code coverage reporting and analysis

**Setup**:
1. Install from: https://github.com/apps/codecov
2. Grant access to `image-preprocessing-detector` repository
3. Add `CODECOV_TOKEN` secret:
   - Navigate to: https://app.codecov.io/gh/williaby/image-preprocessing-detector
   - Copy repository upload token
   - Add to GitHub Secrets: Settings → Secrets → Actions → New repository secret
   - Name: `CODECOV_TOKEN`
   - Value: [paste token]

**Integration**: Already configured in `.github/workflows/ci.yml` (line 194-205)

#### 3. Semgrep
**Purpose**: Static analysis for security vulnerabilities

**Setup**:
1. Sign up at: https://semgrep.dev/
2. Connect GitHub account
3. Add `image-preprocessing-detector` repository
4. Add `SEMGREP_APP_TOKEN` secret:
   - Navigate to: https://semgrep.dev/orgs/-/settings/tokens
   - Create new token
   - Add to GitHub Secrets: Settings → Secrets → Actions → New repository secret
   - Name: `SEMGREP_APP_TOKEN`
   - Value: [paste token]

**Integration**: Already configured in `.github/workflows/security-analysis.yml` (line 162-171)

#### 4. GitGuardian (Optional)
**Purpose**: Secret scanning and credential leak detection

**Setup**:
1. Install from: https://github.com/apps/gitguardian
2. Grant access to `image-preprocessing-detector` repository
3. Free tier: 25 developers, unlimited public repositories

#### 5. StepSecurity (Already Integrated)
**Purpose**: Supply chain security and CI/CD hardening

**Setup**:
1. Sign up at: https://app.stepsecurity.io/
2. Connect GitHub account
3. View insights at: https://app.stepsecurity.io/github/williaby/image-preprocessing-detector/actions/runs

**Integration**: Already configured via `harden-runner` in all workflows

---

## Step 5: Verify Workflows

After pushing to GitHub, verify workflows are running:

### Check Workflow Runs
**Navigate to**: https://github.com/williaby/image-preprocessing-detector/actions

**Expected Workflows**:
1. **CI** (ci.yml)
   - Triggers on push to main
   - Jobs: setup-optimized, test, quality-checks, ci-success, ci-gate
   - Expected duration: ~15-20 minutes

2. **Security Analysis** (security-analysis.yml)
   - Triggers on push to main (initial run)
   - Jobs: codeql-analysis, dependency-security, security-scanning, image-processing-security
   - Expected duration: ~20-25 minutes

3. **OpenSSF Scorecard** (scorecard.yml)
   - Triggers on push to main (initial run)
   - Weekly schedule: Tuesdays at 21:21 UTC
   - Job: analysis
   - Expected duration: ~5-10 minutes

### View CodeQL Results
**Navigate to**: https://github.com/williaby/image-preprocessing-detector/security/code-scanning

**Expected**: CodeQL alerts (likely 0 for initial scan)

### View Scorecard Results
**Navigate to**: https://securityscorecards.dev/viewer/?uri=github.com/williaby/image-preprocessing-detector

**Expected Score**: 7.5-8.0 / 10 (after first run completes)

**Badge Will Automatically Update**: README.md already includes the scorecard badge

---

## Step 6: Verify Badges

After workflows complete, verify badges in README:

**Navigate to**: https://github.com/williaby/image-preprocessing-detector

**Expected Badges** (top of README):
1. ✅ **CI/CD Pipeline** - Green (passing)
2. ✅ **OpenSSF Scorecard** - Showing score (7.5-8.0 / 10)
3. ✅ **Contributor Covenant** - Version 2.1
4. ✅ **Python 3.12** - Blue badge
5. ✅ **Code style: black** - Black badge
6. ✅ **License: MIT** - Yellow badge

**Troubleshooting**:
- If CI badge shows "no status", wait for first workflow run to complete
- If Scorecard badge shows error, wait 24 hours for initial scan
- All other badges are static and should display immediately

---

## Step 7: Post-Setup Verification Checklist

### Repository Structure
- [ ] All files visible in GitHub web UI
- [ ] LICENSE file displays license type correctly
- [ ] SECURITY.md appears in Security tab
- [ ] CODE_OF_CONDUCT.md appears in Insights → Community
- [ ] CONTRIBUTING.md appears in Insights → Community

### Workflows
- [ ] CI workflow completed successfully
- [ ] Security Analysis workflow completed successfully
- [ ] OpenSSF Scorecard workflow completed successfully
- [ ] No workflow failures or errors

### Security
- [ ] Branch protection enabled on `main`
- [ ] CodeQL analysis completed (check Security tab)
- [ ] Dependency review configured
- [ ] Required status checks enforced

### Badges
- [ ] All 6 badges visible in README
- [ ] CI badge shows green/passing
- [ ] OpenSSF Scorecard badge shows score
- [ ] All badge links work correctly

### GitHub Apps
- [ ] Renovate installed and created dependency dashboard
- [ ] Codecov configured and reporting coverage
- [ ] Semgrep configured and running scans
- [ ] StepSecurity dashboard accessible

---

## Step 8: Monitor Initial Activity

### First 24 Hours

**Renovate Bot**:
- [ ] Creates "Dependency Dashboard" issue
- [ ] May create initial update PRs (if dependencies are outdated)
- [ ] Check: https://github.com/williaby/image-preprocessing-detector/issues

**OpenSSF Scorecard**:
- [ ] First scan completes within 24 hours
- [ ] Results uploaded to GitHub Code Scanning
- [ ] Score visible at: https://securityscorecards.dev/viewer/

**CodeQL Analysis**:
- [ ] Scan completes successfully
- [ ] Results visible in Security → Code Scanning
- [ ] No critical/high severity alerts expected

**Codecov**:
- [ ] Coverage report uploaded
- [ ] Coverage dashboard available at: https://app.codecov.io/gh/williaby/image-preprocessing-detector
- [ ] Current coverage: ~80% (from Phase 1 testing)

### First Week

**Renovate PRs**:
- [ ] Review and merge dependency updates
- [ ] Verify auto-merge works for GitHub Actions
- [ ] Check manual review triggers for image processing libraries

**StepSecurity Insights**:
- [ ] Review egress audit logs
- [ ] Identify outbound network patterns
- [ ] Whitelist expected endpoints if needed

**Scorecard Improvements**:
- [ ] Review detailed scorecard findings
- [ ] Address any low-scoring criteria
- [ ] Track score improvements over time

---

## Expected OpenSSF Scorecard Results

### Initial Score (First Run): 7.5-8.0 / 10

**High Scores (9-10/10)**:
- Binary-Artifacts: 10/10
- CI-Tests: 10/10
- Dangerous-Workflow: 10/10
- Dependency-Update-Tool: 10/10 ✨ (Renovate)
- License: 10/10 ✨ (LICENSE file)
- Maintained: 10/10
- Pinned-Dependencies: 10/10 ✨ (SHA256 pinning)
- SAST: 10/10
- Security-Policy: 10/10 ✨ (SECURITY.md)
- Token-Permissions: 10/10
- Vulnerabilities: 10/10

**Medium Scores (5-8/10)**:
- Branch-Protection: 8-9/10 ✨ (after enabling in Step 3)
- Code-Review: 7-8/10 ✨ (CODEOWNERS + branch protection)
- Contributors: 5/10 (single contributor, natural growth)
- Packaging: 5/10 (not published to PyPI yet)

**Low Scores (0-4/10)**:
- CII-Best-Practices: 0/10 (not enrolled, optional)
- Fuzzing: 0/10 (planned for Phase 2)
- Signed-Releases: 0/10 (no releases yet, planned Phase 4)

---

## Troubleshooting Common Issues

### Issue: "Repository not found" when pushing
**Solution**: Create repository on GitHub first (see Step 1)

### Issue: Workflows fail with permission errors
**Solution**:
- Check `permissions:` blocks in workflow files
- Ensure repository settings allow GitHub Actions to create PRs
- Navigate to: Settings → Actions → General → Workflow permissions
- Select: "Read and write permissions"
- Enable: "Allow GitHub Actions to create and approve pull requests"

### Issue: Codecov upload fails
**Solution**:
- Add `CODECOV_TOKEN` secret (see Step 4.2)
- Verify token is valid
- Check workflow logs for specific error

### Issue: Semgrep fails with authentication error
**Solution**:
- Add `SEMGREP_APP_TOKEN` secret (see Step 4.3)
- Verify token has correct permissions
- Check if Semgrep App is installed on repository

### Issue: Renovate doesn't create PRs
**Solution**:
- Wait 24-48 hours for initial scan
- Check Dependency Dashboard issue for status
- Verify `renovate.json` is valid JSON
- Check Renovate logs: https://app.renovatebot.com/dashboard

### Issue: OpenSSF Scorecard badge shows error
**Solution**:
- Wait 24-48 hours for initial scan
- Verify repository is public
- Check workflow completed successfully
- Manual trigger: Actions → OpenSSF Scorecard → Run workflow

### Issue: Branch protection prevents pushing
**Solution**:
- Disable branch protection temporarily for initial setup
- Or: Push to feature branch first, create PR to main
- Or: Exempt administrators from branch protection (not recommended)

---

## Next Steps After Setup

### Immediate (Today)
1. Complete Steps 1-7 above
2. Verify all workflows pass
3. Review OpenSSF Scorecard results
4. Check Renovate dependency dashboard

### This Week
1. Review and merge Renovate PRs
2. Monitor StepSecurity egress logs
3. Address any CodeQL findings
4. Improve scorecard score if needed

### Phase 1 Completion
1. Complete MVP implementation (Week 4-7)
2. Maintain 80%+ test coverage
3. Document API changes
4. Prepare Phase 1 completion PR

### Phase 2 Planning
1. Enable ML dependencies in renovate.json
2. Implement fuzzing (improve scorecard)
3. Add performance benchmarks
4. Plan PyPI publishing workflow

---

## Support and Resources

### Documentation
- OpenSSF Scorecard: https://github.com/ossf/scorecard
- Renovate Docs: https://docs.renovatebot.com/
- StepSecurity Docs: https://docs.stepsecurity.io/
- GitHub Actions Security: https://docs.github.com/en/actions/security-guides

### Project Documentation
- [SECURITY.md](SECURITY.md) - Security policy and reporting
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Community standards
- [README.md](README.md) - Project overview and quick start

### Analysis Documents
- [tmp_cleanup/.tmp-openssf-scorecard-analysis-20251105.md](tmp_cleanup/.tmp-openssf-scorecard-analysis-20251105.md) - Detailed scorecard analysis
- [tmp_cleanup/.tmp-badge-integration-complete-20251105.md](tmp_cleanup/.tmp-badge-integration-complete-20251105.md) - Implementation summary

---

## Commit History Reference

**Latest Commit**: `378d6e4` - Badge infrastructure
```
feat: add OpenSSF Scorecard and Contributor Covenant badge infrastructure

Implements comprehensive security, community, and dependency management
infrastructure to achieve OpenSSF Scorecard compliance and professional
open-source project standards.
```

**Previous Commits**:
- `91bd5b3` - Phase 1 kickoff and PDF ingestion implementation
- `d4af75e` - Complete Phase 0 - Foundation & Scaffolding

---

**Ready to Proceed**: Follow Step 1 to create the GitHub repository, then execute remaining steps sequentially.

**Estimated Setup Time**: 30-45 minutes (including waiting for workflow runs)

**Questions?**: See [CONTRIBUTING.md](CONTRIBUTING.md) or contact byronawilliams@gmail.com
