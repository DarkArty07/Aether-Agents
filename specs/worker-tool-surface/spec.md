# Worker tool surface adjustment

The owner requested disabling computer_use and clarify for Supervisor and all
Implementer instances, enabling the same Exa search/extraction backend as Morfeo,
and normal commit/PR/check/merge closeout to main. This is a bounded native
configuration change, not a new framework/policy feature or an Objective Contract.

Use native agent.disabled_toolsets across platform resolution. Preserve all other
tools, providers, models, approvals, SOUL and work. Existing credentials may be
reused locally only for the explicitly authorized roles; never publish values.

Acceptance: portable resource regressions; effective native CLI/Telegram schemas
exclude both tools and include web_search/web_extract with provisioned Exa; actual
bounded Exa search and extraction under each worker profile; no source/profile
change outside those settings; normal required CI/PR merge with clean scoped diff.

Current R0 constitution and role authority are unchanged. No project canonical
skills are named for this bounded configuration change. Root AGENTS guidance remains
applicable and needs no edit; it already excludes private runtime/credentials from
public source. Issue #383 owns intake tracking; storage incident #382 is separate.

Compatibility: patch (correct worker defaults using existing public Hermes keys),
release_action=defer, release_channel=none. No package release or deployment.
