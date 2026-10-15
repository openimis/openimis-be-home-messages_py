# openIMIS Backend Home Messages Module

Home Messages provides Django models and GraphQL operations for messages and their file or URL attachments in openIMIS.

- Repository: [openimis/openimis-be-home-messages_py](https://github.com/openimis/openimis-be-home-messages_py)
- Python distribution: `openimis-be-home-messages`
- Python package and Django app label: `notice`
- Django configuration: `notice.apps.NoticeConfig`, displayed as **Home Messages**
- Frontend: [openimis/openimis-fe-home-messages_js](https://github.com/openimis/openimis-fe-home-messages_js), packaged as `@openimis/fe-home-messages`

## Assembly integration

Register the module in the backend assembly's `openimis.json`:

```json
{
  "name": "notice",
  "pip": "git+https://github.com/openimis/openimis-be-home-messages_py.git@develop#egg=openimis-be-home-messages"
}
```

`develop` is a development example. Pin a reviewed commit or release tag for a reproducible deployment. Follow the assembly's dependency-generation and installation workflow after changing its manifest.

Keep the assembly name as `notice`: the distribution name and Django import name are different. The assembly must also provide Core and Location, which supply base models, GraphQL helpers, configuration, and health facilities.

For an editable local checkout in the backend environment:

```sh
pip install -e /path/to/openimis-be-home-messages_py
```

If replacing an installed `openimis-be-notice` distribution, uninstall that distribution before installing the renamed one. Both provide the same `notice` Python package and should not be installed together. Existing Docker checkouts may still use `/app/modules/openimis-be-notice_py`; use the actual checkout path.

On a new installation, run the assembly's normal Django migrations. The rename itself requires no new migration or data reset.

## Models

Both message and attachment models inherit `core.models.VersionedModel`.

| Model | Database table | Purpose |
| --- | --- | --- |
| `Notice` | `tblNotices` | Message content, priority, audience, and publication fields |
| `NoticeAttachment` | `tblNoticeAttachments` | File or URL attachments linked to a message |
| `NoticeMutation` | `notice_NoticeMutation` | Links messages to Core mutation logs |

### Messages

`Notice` uses an integer `id` primary key and a separate unique, 36-character `uuid`. It stores:

- `title`: up to 255 characters at the model level.
- `description`: message content.
- `priority`: `LOW`, `MEDIUM`, or `HIGH`; the model default is `MEDIUM`.
- `health_facility`: optional audience restriction; null represents no specific facility.
- `created_at`, `updated_at`, and inherited validity/history fields.
- `is_active`, `schedule_publish`, and optional `publish_start_date`.
- `audit_user_id`.

Publication fields describe stored state; clients should not assume that the existence of scheduling fields alone guarantees an automatic publishing workflow.

### Attachments

`NoticeAttachment` has an integer primary key and a separate unique UUID. Its `notice` foreign key uses the reverse relation `notice_attachments`.

`general_type` is `FILE` or `URL`. Other fields include title, type description, date, filename, MIME type, URL, and Base64 document content. The `module` field retains the value `notice` for compatibility.

## GraphQL

The API retains its existing Notice names. Queries return Relay connections with `totalCount`, `pageInfo`, and `edges { node { ... } }`.

### Queries

- `notices`: paginated message lookup, with filters defined in `notice/gql_queries.py`. Retrieve one message using its `uuid` filter; there is no separate singular `notice` query registered by this module.
- `noticeAttachments`: paginated attachment lookup, including `notice_Uuid` filtering.

Example:

```graphql
query PublishedMessages {
  notices(isActive: true, first: 10) {
    totalCount
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        uuid
        title
        description
        priority
        createdAt
        isActive
        healthFacility { code name }
        attachmentCount
      }
    }
  }
}
```

Use the returned cursor with `after` to request subsequent pages. Supported query filters include title and description containment, priority, active status, publication dates, and health-facility fields. `showHistory` controls the resolver's default validity filtering; consult the schema for exact generated argument names.

### Mutations

- `createNotice`
- `updateNotice`
- `deleteNotice`
- `toggleNoticeStatus`
- `createNoticeAttachment`
- `updateNoticeAttachment`
- `deleteNoticeAttachment`

Input definitions and validation are implemented in `notice/gql_mutations.py`. Message mutation-log links are handled through the Core mutation signal integration in `notice/schema.py`.

## Permissions and row security

Permission defaults are loaded through `core.models.ModuleConfiguration` under the module name `notice`.

| Configuration key | Default permission |
| --- | --- |
| `gql_query_notices_perms` | `112001` |
| `gql_mutation_create_notices_perms` | `112002` |
| `gql_mutation_update_notices_perms` | `112003` |
| `gql_mutation_delete_notices_perms` | `112004` |
| `gql_mutation_toggle_notice_status_perms` | `112005` |
| `gql_mutation_send_notice_email_perms` | `112006` |
| `gql_mutation_send_notice_sms_perms` | `112007` |

Email/SMS permission settings do not imply that separate email/SMS mutations are registered in this module's schema.

When the assembly enables `ROW_SECURITY`, the message queryset limits non-admin users to messages without a facility restriction or messages for their own facility. Superusers and IMIS administrators bypass that facility restriction. Anonymous users receive no message rows through this queryset when row security is enabled. Query permission checks also apply.

## Configuration

`notice/apps.py` defines `DEFAULT_CFG` and loads overrides when the app initializes. Besides permissions, declared defaults include:

| Key | Default |
| --- | --- |
| `notice_max_length_title` | `100` |
| `notice_max_length_description` | `1000` |
| `notice_priority_options` | `["Low", "Medium", "High"]` |
| `notice_default_priority` | `"Low"` |
| `notice_max_restore` | `null` |
| `notice_email_enabled` | `true` |
| `notice_sms_enabled` | `true` |
| `notice_attachments_root_path` | `null` |
| `allowed_domains_attachments` | `[]` |

These are application configuration defaults, not a replacement for model definitions or mutation validation. For example, the model's priority default is `MEDIUM`, while the configuration declares `Low`. Check the consuming code before relying on a setting to change behavior.

## Rename compatibility

The repositories are now `openimis-be-home-messages_py` and `openimis-fe-home-messages_js`. The Python distribution is renamed, but imports, the Django app label, configuration namespace, GraphQL names, database tables, and migration history retain `notice`.

Do not rename the `notice/` directory or rewrite historical migrations as part of this package rename. Existing installations retain their data. Local checkout folders may keep their previous names.

Changing repository metadata does not publish a PyPI release. Use the Git source above, an editable checkout, or an available published release.

## Source map

- `setup.py`: distribution metadata and declared dependencies.
- `notice/apps.py`: app registration and configuration defaults.
- `notice/models.py`: database models.
- `notice/schema.py`: query/mutation registration and mutation signals.
- `notice/gql_queries.py`: GraphQL types, filters, and message row security.
- `notice/gql_mutations.py`: mutation inputs and behavior.
- `notice/migrations/`: database migration history.
