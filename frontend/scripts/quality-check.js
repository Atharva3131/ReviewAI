#!/usr/bin/env node
/**
 * Frontend Code Quality Check Script
 * Runs all code quality checks for the frontend codebase.
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// Color codes for terminal output
const colors = {
  green: '\x1b[92m',
  red: '\x1b[91m',
  yellow: '\x1b[93m',
  blue: '\x1b[94m',
  reset: '\x1b[0m',
};

function printHeader(message) {
  console.log(`\n${colors.blue}${'='.repeat(80)}${colors.reset}`);
  console.log(`${colors.blue}${message.padStart((80 + message.length) / 2).padEnd(80)}${colors.reset}`);
  console.log(`${colors.blue}${'='.repeat(80)}${colors.reset}\n`);
}

function printSuccess(message) {
  console.log(`${colors.green}✓ ${message}${colors.reset}`);
}

function printError(message) {
  console.log(`${colors.red}✗ ${message}${colors.reset}`);
}

function printWarning(message) {
  console.log(`${colors.yellow}⚠ ${message}${colors.reset}`);
}

function runCommand(command, description, allowFailure = false) {
  console.log(`\n${colors.yellow}Running: ${description}${colors.reset}`);
  console.log(`Command: ${command}`);

  try {
    execSync(command, {
      stdio: 'inherit',
      cwd: path.join(__dirname, '..'),
    });
    printSuccess(`${description} passed`);
    return true;
  } catch (error) {
    if (allowFailure) {
      printWarning(`${description} failed (non-blocking)`);
      return false;
    } else {
      printError(`${description} failed`);
      return false;
    }
  }
}

function checkESLint() {
  return runCommand(
    'npm run lint',
    'ESLint code linting'
  );
}

function checkPrettier() {
  return runCommand(
    'npm run format:check',
    'Prettier formatting check'
  );
}

function checkTypeScript() {
  return runCommand(
    'npm run type-check',
    'TypeScript type checking'
  );
}

function checkDependencies() {
  return runCommand(
    'npx depcheck',
    'Unused dependencies check',
    true
  );
}

function checkNpmAudit() {
  return runCommand(
    'npm audit --audit-level=moderate',
    'npm security audit',
    true
  );
}

function checkBundleSize() {
  console.log(`\n${colors.yellow}Running: Bundle size analysis${colors.reset}`);
  
  try {
    // Check if .next directory exists
    const nextDir = path.join(__dirname, '..', '.next');
    if (!fs.existsSync(nextDir)) {
      printWarning('Build directory not found. Run npm run build first.');
      return true; // Don't fail if build doesn't exist
    }

    execSync('npm run build', {
      stdio: 'inherit',
      cwd: path.join(__dirname, '..'),
    });

    printSuccess('Bundle size analysis completed');
    return true;
  } catch (error) {
    printWarning('Bundle size analysis failed (non-blocking)');
    return false;
  }
}

function fixFormatting() {
  printHeader('Auto-fixing Code Formatting');

  const eslintSuccess = runCommand(
    'npm run lint:fix',
    'ESLint auto-fix'
  );

  const prettierSuccess = runCommand(
    'npm run format',
    'Prettier auto-format'
  );

  return eslintSuccess && prettierSuccess;
}

function main() {
  // Parse command line arguments
  const fixMode = process.argv.includes('--fix');

  if (fixMode) {
    printHeader('Frontend Code Quality - Fix Mode');
    if (fixFormatting()) {
      printSuccess('\nFormatting fixes applied successfully!');
      process.exit(0);
    } else {
      printError('\nSome formatting fixes failed');
      process.exit(1);
    }
  }

  printHeader('Frontend Code Quality Checks');

  const results = {};

  // Run all checks
  printHeader('Code Linting');
  results.eslint = checkESLint();

  printHeader('Code Formatting');
  results.prettier = checkPrettier();

  printHeader('Type Checking');
  results.typescript = checkTypeScript();

  printHeader('Dependency Analysis');
  results.dependencies = checkDependencies();

  printHeader('Security Checks');
  results.audit = checkNpmAudit();

  printHeader('Bundle Analysis');
  results.bundle = checkBundleSize();

  // Print summary
  printHeader('Quality Check Summary');

  const passed = Object.values(results).filter(v => v).length;
  const total = Object.keys(results).length;

  for (const [check, success] of Object.entries(results)) {
    if (success) {
      printSuccess(`${check.charAt(0).toUpperCase() + check.slice(1)}: PASSED`);
    } else {
      printError(`${check.charAt(0).toUpperCase() + check.slice(1)}: FAILED`);
    }
  }

  console.log(`\n${colors.blue}Results: ${passed}/${total} checks passed${colors.reset}`);

  if (passed === total) {
    printSuccess('\n✓ All quality checks passed!');
    process.exit(0);
  } else {
    printError(`\n✗ ${total - passed} quality check(s) failed`);
    printWarning('\nRun with --fix to auto-fix formatting issues');
    process.exit(1);
  }
}

main();
