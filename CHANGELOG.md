# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [DjangoVer](https://www.b-list.org/weblog/2024/nov/18/djangover/) for release numbering.

## [Unreleased]

### Added
- A Django conversations app for persisting and reconstructing Pydantic AI `Conversation` objects by their conversation ID, with queryable usage counters.
- Django-backed persistent memory storage for Pydantic AI Harness, scoped by directory and supporting file reads, writes, deletes, path listing, and lexical search.
- Django models and an initial migration for memory directories, stored files, and idempotent operation receipts. Write versions use SHA-256 content hashes, while delete mutations return `None` as their version.
