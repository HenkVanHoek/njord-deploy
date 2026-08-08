---
name: obsidian-logbook
description: Export and save a formatted chat summary of the active session to Henks Geheugen (Obsidian vault), complete with timestamp, project name, deep link to the Antigravity conversation, and Obsidian component/module tags.
---

# Obsidian Logbook Export Skill

Use this skill to automatically summarize the current Antigravity chat session and save it as a structured Markdown note in the user's Obsidian vault ("Henks Geheugen").

## Obsidian Vault Configuration
- **Vault Root**: `/home/hvhoek/Nextcloud/Henks Geheugen`
- **Project Folder**: `/home/hvhoek/Nextcloud/Henks Geheugen/Projecten/<ProjectName>/Logboek/`
  *(Default project name for this repo: `Njord-deploy`)*

## Summary File Requirements

### 1. File Path & Naming Convention
- Directory: `/home/hvhoek/Nextcloud/Henks Geheugen/Projecten/<ProjectName>/Logboek/`
- Filename format: `YYYY-MM-DD_HHmm_<korte-onderwerp-titel>.md`
  - Example: `2026-08-07_1505_Obsidian_Chat_Logger_Skill.md`

### 2. Header & YAML Frontmatter
Every note must begin with standardized YAML frontmatter for Obsidian querying and tag filtering:

```yaml
---
date: YYYY-MM-DD HH:mm
project: <ProjectName>
conversation_id: <conversation-id>
tags:
  - logboek
  - <project-name-lowercase>
  - <component-tag-1>
  - <component-tag-2>
---
```

### 3. Markdown Note Structure

```markdown
# 📝 Chat Log: [Beknopte Onderwerp Titel]

- **Datum/Tijd**: YYYY-MM-DD HH:mm
- **Project**: [Project Naam]
- **Betrokken componenten**: `#tag1` `#tag2` `#tag3`
- **Antigravity Chat**: [Bekijk volledige chat in Antigravity](conversation://<conversation-id>)

---

## 🎯 Doel van de Sessie
[Beknopte beschrijving van de vraag/opdracht van de gebruiker]

## 🛠️ Uitgevoerde Acties & Code Wijzigingen
- **[Onderwerp 1]**: Beschrijving van de wijziging of analyse.
- **[Onderwerp 2]**: Beschrijving van de wijziging of analyse.

## 🏷️ Betrokken Software & Componenten
- **Modules**: e.g., `configurator_app`, `editor_app`, `component_manager`, `ssh_manager`
- **Services/Templates**: e.g., `adguard-home`, `open-webui`, `ollama`
- **Infrastructuur**: e.g., Proxmox, Ansible, Docker Engine, LXC

## 🧪 Test- en Kwaliteitsresultaten
- Status van `pytest`, `pre-commit`, `flake8`, `mypy` en functionaliteitscontroles.

## 📌 Vervolgstappen / Openstaande punten
- Eventuele vervolgacties voor een volgende sessie.
```

## Tagging System Rules
When exporting to Obsidian, analyze the chat content and automatically apply relevant tags:
1. **Core Architecture**: `#configurator`, `#editor`, `#managers`, `#utils`, `#templates`, `#scripts`, `#docs`, `#tests`
2. **Infrastructure & DevOps**: `#proxmox`, `#ansible`, `#docker`, `#lxc`, `#ssh`, `#git`, `#release`
3. **Specific Services**: `#open-webui`, `#ollama`, `#adguard-home`, `#pihole`, etc.
4. **General Topic**: `#feature`, `#bugfix`, `#refactor`, `#documentation`, `#skill`

## Workflow Procedure
1. Create the `Logboek/` directory under `/home/hvhoek/Nextcloud/Henks Geheugen/Projecten/<ProjectName>/Logboek` if it does not already exist.
2. Determine current date/time (e.g. `2026-08-07 15:05`) and extract the current conversation ID.
3. Draft a thorough, clear summary of the chat session in Dutch.
4. Write the file to the Obsidian vault using `write_to_file`.
5. Ensure the file ends with a trailing empty line.
6. Provide a clickable file link to the created Obsidian note in your final response to the user.
