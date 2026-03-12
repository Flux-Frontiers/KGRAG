# Changelog & Commit Workflow

You will analyze staged git changes, update the CHANGELOG.md, and prepare a commit message. Execute the following steps in sequence:

## Step 0: Verify Files Are Staged

1. Check if files are already staged with `git status`
2. If no files are staged, remind the user to stage files first:
   - `git add <files>` for specific files
   - `git add -A` for all changes
3. Proceed only after files are staged

## Step 1: Analyze Staged Changes

1. Run `git status` to identify staged files
2. Run `git diff --staged` to examine the actual changes
3. Analyze what has been modified, added, or removed

## Step 2: Update CHANGELOG.md

1. Read the existing `CHANGELOG.md` file to understand the format
2. Determine the appropriate section for the new entry:
   - If an "Unreleased" section exists, add there
   - Otherwise, add to the current version section
3. Write a new changelog entry that:
   - Summarizes the changes concisely but informatively
   - Explains what changed and why
   - Follows the existing format and style conventions
   - Uses appropriate categories (Added, Changed, Fixed, Removed, etc.)
4. Update the CHANGELOG.md file with the new entry
5. **Stage CHANGELOG.md** with `git add CHANGELOG.md` so it is included in the commit

## Step 3: Create Commit Message

1. Draft a commit message following conventional commit format:
   ```
   type(scope): brief summary

   Detailed explanation if needed
   ```

2. Determine the appropriate type:
   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation changes
   - `refactor`: Code refactoring
   - `test`: Test changes
   - `chore`: Maintenance tasks
   - `style`: Code style changes
   - `perf`: Performance improvements

3. Write a clear, concise summary (50 chars or less for first line)
4. Add detailed explanation in body if needed
5. Save the commit message to `commit.txt` in the project root

## Important Rules

- **Do NOT execute `git commit`** - only prepare the commit message file
- Be thorough in analyzing changes before writing summaries
- Follow the project's existing conventions for both changelog and commits
- If CHANGELOG.md doesn't exist, note this and skip that step

## Completion

After completing all steps, present:
```
✓ Analyzed staged changes
✓ Updated CHANGELOG.md
✓ Staged CHANGELOG.md
✓ Created commit.txt

Ready to commit with: git commit -F commit.txt
```
