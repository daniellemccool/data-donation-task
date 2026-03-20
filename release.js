#!/usr/bin/env node

const shell = require('shelljs');
const archiver = require('archiver');
const fs = require('fs');
const path = require('path');

// Set environment
process.env.NODE_ENV = 'production';

// Get project name from current directory
const name = path.basename(process.cwd());

// Get branch name, sanitize slashes
const { execFileSync } = require('child_process');
let branch;
try {
  branch = execFileSync('git', ['branch', '--show-current'], { encoding: 'utf8' }).trim();
} catch {
  branch = 'unknown';
}
branch = branch.replace(/\//g, '-');

// Create releases directory if it doesn't exist
shell.mkdir('-p', 'releases');

// Get timestamp
const timestamp = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format

console.log('Building all-platform release...');
if (shell.exec('pnpm run build').code !== 0) {
  shell.echo('Error: Build failed');
  shell.exit(1);
}

// Create zip file
const distPath = path.join('packages', 'data-collector', 'dist');
const zipFileName = `${name}_all_${branch}_${timestamp}.zip`;
const zipPath = path.join('releases', zipFileName);

console.log(`Creating release: ${zipFileName}`);

const output = fs.createWriteStream(zipPath);
const archive = archiver('zip', {
  zlib: { level: 9 } // Maximum compression
});

output.on('close', () => {
  console.log(`Release created successfully: ${zipPath}`);
  console.log(`Total bytes: ${archive.pointer()}`);
});

archive.on('error', (err) => {
  throw err;
});

archive.pipe(output);
archive.directory(distPath, false);
archive.finalize();