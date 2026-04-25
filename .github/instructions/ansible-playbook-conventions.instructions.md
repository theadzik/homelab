---
description: "Use when editing Ansible playbooks, role tasks/defaults, or vars under ansible/. Enforces role/task structure, idempotency safeguards, and variable placement conventions for this repository."
name: "Ansible Playbook Conventions"
applyTo: "ansible/**/*.y*ml"
---

# Ansible Playbook Conventions

Apply these rules for changes in ansible playbooks and roles.

## Scope And Sources

- Follow the main playbook flow in [ansible/playbooks/local-setup.yaml](../../ansible/playbooks/local-setup.yaml).
- Keep shared play variables in [ansible/playbooks/vars/local-common.yaml](../../ansible/playbooks/vars/local-common.yaml).
- Keep role-specific defaults in `ansible/playbooks/roles/<role>/defaults/main.yaml`.
- Keep executable steps in `ansible/playbooks/roles/<role>/tasks/main.yaml`.

## Role And Task Patterns

- Prefer built-in modules over shell/command when a module exists (`apt`, `file`, `copy`, `systemd`, `git`, `uri`, `apt_repository`).
- Use fully qualified module names (`ansible.builtin.*`, `community.general.*`).
- Give every task a clear `name` and keep one responsibility per task.
- Use loops for package/tool lists instead of duplicated tasks.
- Put privilege escalation only where needed (`become: true` on the task/block requiring it).
- For OS- or environment-specific steps, use explicit conditions or blocks.
- Avoid editing `/etc/passwd` directly; use `ansible.builtin.user` for shell/account updates.
- Prefer modern apt keyring flow (`get_url` + `signed-by=`) over `apt_key`.

## Idempotency Rules

- Shell/command tasks must include idempotency guards such as `creates`, `removes`, or explicit `changed_when`/`failed_when` logic.
- If a task can trigger service restarts, gate restart with a registered change flag.
- Avoid non-deterministic writes; do not replace files when content is unchanged.
- Prefer declarative end-state modules over imperative command sequences.
- Keep tasks re-runnable without side effects on repeated execution.
- For network download/install tasks, do not resolve "latest" dynamically. Prefer package-manager installs or pinned artifact URLs with explicit version and expected SHA256.
- For security-sensitive binaries, require fail-fast checksum verification (`assert`) so the playbook stops on mismatch.

## Variable Placement

- Put cross-role values in [ansible/playbooks/vars/local-common.yaml](../../ansible/playbooks/vars/local-common.yaml).
- Put role-owned defaults in `roles/<role>/defaults/main.yaml`.
- Do not hardcode user-specific paths if `ansible_user`-based paths are already used in the role.
- Keep computed values in defaults/vars and reference them from tasks rather than duplicating expressions.
- For files written to system paths, set explicit `owner`, `group`, and `mode` unless defaults are intentionally required.

## Package State Conventions

- Follow existing repository intent:
- Use `state: latest` for actively managed CLI/tooling updates.
- Use `state: present` for base prerequisites that do not need forced upgrades.
- Use `cache_valid_time` or `update_cache` intentionally when apt package freshness matters.

## Completion Checks

- Syntax-check after edits:
- `ansible-playbook ansible/playbooks/local-setup.yaml --syntax-check`
- For risky task changes, validate with check mode when feasible:
- `ansible-playbook ansible/playbooks/local-setup.yaml --check`
- If a task is intentionally non-idempotent, document why in a short task comment.
