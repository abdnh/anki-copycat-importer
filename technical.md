Some incomplete notes about AnkiApp's internals.

_Note: The add-on no longer imports from the SQLite database as of version 3.0.0_

## Terminology

AnkiApp's uses familiar terms like decks, cards, and tags, with some differences:

- `knol`: a "knol" can be thought of as the counterpart of a note in Anki.[^1]
- `layout`: a layout is like a notetype with a single card type in Anki.

## Tables

The database has the following tables:

### knol_values

This table contains the contents of each note field in the following format:

| id                               | knol_id                          | knol_key_name | value                           |
| -------------------------------- | -------------------------------- | ------------- | ------------------------------- |
| 7df6b7685e0a44bcbbf562637efe1c96 | 001c3c5b71f945e29c45368c0237cb08 | Front         | What is the capital of Ukraine? |
| a82b69c4abd14b92b6ad12c3743bde76 | 001c3c5b71f945e29c45368c0237cb08 | Back          | Kyiv                            |
| 79606c0a79324d9c841a7c92a3784481 | 0012a6ae0a0847838937fcbd18ea16d1 | Word          | ebb                             |
| 7b0b88f4398c417ebe22c7a1c49e3ada | 0012a6ae0a0847838937fcbd18ea16d1 | Translation   | جزر                             |
| e0283190c4444d1b9f71933b0157fbaf | 0012a6ae0a0847838937fcbd18ea16d1 | Extra         | See "ebb and flow"              |

As you can guess, `knol_key_name` is the field name and `value` contains the field contents.
Rows that have the same `knol_id` value belongs to the same note.

### knol_keys

This table containts (apparently) redundant data about the names of fields that can be obtained from `knol_values` too.
It's ignored by the add-on.

| name  |
| ----- |
| Front |
| Back  |
| Extra |

### knols

This table just contains the IDs of knols:

| id                               |
| -------------------------------- |
| 001c3c5b71f945e29c45368c0237cb08 |
| 0012a6ae0a0847838937fcbd18ea16d1 |

Again, this seems redundant with the existence of the `knol_values` table.

### knol_blobs

This table stores media files:

| id                               | knol_value_id                    | type       | value         |
| -------------------------------- | -------------------------------- | ---------- | ------------- |
| 1d8359fe48c04bebbbc52e2b0f7ed4d1 | d8e840834f1d4c12aa0b99d56013693e | image/gif  | R0lGODlhk...  |
| 46872580a15d4fdda1931bd54f2d08af | 0d783dc044024ee1adfafd707c1af9e2 | image/jpeg | /9j/4AAQSk... |
| 708c2c0cac1641df881ed6ba8a2f1e0c | 7a8b667a277c4bf8b55e81cc5c88c4dd | image/webp | UklGR...      |

- `knol_value_id`: the ID of the `knol_values` row where the media file is used (which implies that there can be duplicate files with the exact same contents used in different fields or notes.)
- `type`: the [MIME type](https://en.wikipedia.org/wiki/Media_type) of the file.
- `value`: the Base64-encoded contents of the file.

The IDs of media files are referenced in fields (knol_values->value columns) like this:

```
{{blob 1d8359fe48c04bebbbc52e2b0f7ed4d1}}
```

NOTE: It appears that with recent AnkiApp versions (6.1.0), media files are [no longer stored](https://forums.ankiweb.net/t/ankiapp-importer/16734/52) in the `knol_blobs` table.
Instead, they are stored as normal files separetely from the database file.

### layouts

The `layouts` table has the following format:

| id                               | name          | templates                                                                 | style                         | response_type_id                 | status |
| -------------------------------- | ------------- | ------------------------------------------------------------------------- | ----------------------------- | -------------------------------- | ------ |
| acf3bd5e3fc94d64a9b21d7a531a6563 | Front-to-Back | `["<div>{{Front}}</div>","<div>{{front}}</div><hr/><div>{{Back}}</div>"]` | `div { font-size: x-large; }` | 5b4f816026f511e2aac3001e52fffe46 | 0      |
| a4abf3245c0340c39e43216fcd714dfc | Translation   | `["<div>{{Word}}</div>","<div>{{Translation}}</div>"]`                    | `div { font-size: x-large; }` | 5b4f816026f511e2aac3001e52fffe46 | 0      |

- `templates`: the front and back templates stored as a string representation of a Python list (apparently).
- `style`: CSS styles
- `response_type_id`: TODO
- `status`: TODO

### knol_keys_layouts

This table maps each field to its layout:

| layout_id                        | knol_key_name |
| -------------------------------- | ------------- |
| 8fe1b4d10fbf403f875b53645bb0bd7e | Front         |
| 8fe1b4d10fbf403f875b53645bb0bd7e | Back          |
| a4abf3245c0340c39e43216fcd714dfc | Word          |
| a4abf3245c0340c39e43216fcd714dfc | Translation   |
| a4abf3245c0340c39e43216fcd714dfc | Extra         |

### knols_tags

This contains the tags of each note.

| knol_id                          | tag_name  |
| -------------------------------- | --------- |
| 001c3c5b71f945e29c45368c0237cb08 | Geography |
| 0012a6ae0a0847838937fcbd18ea16d1 | English   |

### decks

The `decks` table has the following format:

| id                               | status | name             | description        | created_at               | modified_at              | layout_id                        |
| -------------------------------- | ------ | ---------------- | ------------------ | ------------------------ | ------------------------ | -------------------------------- |
| a4dde94984644cf3a749a1898e47261c | 1      | Geography Trivia |                    | 2020-06-28T21:17:30.239Z | 2020-06-28T21:17:30.239Z | 8fe1b4d10fbf403f875b53645bb0bd7e |
| 3662fdc90bfe4a86b11499101b298ecd | 1      | English          | English Vocabulary | 2020-07-13T17:14:10.219Z | 2020-07-13T17:14:10.219Z | a4abf3245c0340c39e43216fcd714dfc |

- `status`: TODO
- `created_at` and `modified_at` are UTC times in the [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) format.
- `layout_id`: AnkiApp associates each deck with a single layout, so moving cards from one deck to another with a different layout [can cause problems](https://forums.ankiweb.net/t/ankiapp-importer/16734/14).

### cards

Cards are stored in the following format:

| id                               | knol_id                          | layout_id                        | created_at    | modified_at   | score_mean        | score_standard_deviation | last_response_at         | num_responses |
| -------------------------------- | -------------------------------- | -------------------------------- | ------------- | ------------- | ----------------- | ------------------------ | ------------------------ | ------------- |
| 1ea545da042dd9155bb04272ab7b7f45 | 001c3c5b71f945e29c45368c0237cb08 | acf3bd5e3fc94d64a9b21d7a531a6563 | 1646433031244 | 1646433031244 | 0.761578857898712 | 0.0322830599592049       | 2021-06-03T20:12:03.105Z | 5             |
| a0f508207855d53210bccff65c0bfdfb | 0012a6ae0a0847838937fcbd18ea16d1 | a4abf3245c0340c39e43216fcd714dfc | 1646433031245 | 1646433031245 | NULL              | NULL                     | NULL                     | 0             |

Most of the columns should be self-explanatory at this point, except:

- `score_mean`: TODO
- `score_standard_deviation`: TODO
- `last_response_at`: date of last review.
- `num_responses`: number of reviews of this card.

### cards_decks

This table tells us in which deck is each card:

| card_id                          | deck_id                          |
| -------------------------------- | -------------------------------- |
| 1ea545da042dd9155bb04272ab7b7f45 | a4dde94984644cf3a749a1898e47261c |
| a0f508207855d53210bccff65c0bfdfb | 3662fdc90bfe4a86b11499101b298ecd |

### decks_knols

This table apparently associates knols with decks like it's done for cards for some reason:

| knol_id                          | deck_id                          |
| -------------------------------- | -------------------------------- |
| 001c3c5b71f945e29c45368c0237cb08 | a4dde94984644cf3a749a1898e47261c |
| 0012a6ae0a0847838937fcbd18ea16d1 | 3662fdc90bfe4a86b11499101b298ecd |

TODO: understand what is the purpose of this.

### decks_layouts

We said earlier that AnkiApp associates each deck with a single layout as implied
by the existence of the `layout_id` column in the `decks` table. But here, with data taken from the wild,
we see that a deck can be associated with multiple layouts (!):

| deck_id                          | layout_id                        |
| -------------------------------- | -------------------------------- |
| a4dde94984644cf3a749a1898e47261c | 8fe1b4d10fbf403f875b53645bb0bd7e |
| a4dde94984644cf3a749a1898e47261c | a4abf3245c0340c39e43216fcd714dfc |
| a4dde94984644cf3a749a1898e47261c | acf3bd5e3fc94d64a9b21d7a531a6563 |
| 3662fdc90bfe4a86b11499101b298ecd | a4abf3245c0340c39e43216fcd714dfc |

I have no idea how AnkiApp uses this table. It's not used by the add-on since
in Anki decks and notetypes are not tied together in any way.

### decks_tags

Apparently decks can have tags too. This table stores each deck's tags:

| deck_id                          | tag_name  |
| -------------------------------- | --------- |
| a4dde94984644cf3a749a1898e47261c | geography |
| a4dde94984644cf3a749a1898e47261c | capitals  |
| 3662fdc90bfe4a86b11499101b298ecd | english   |
| 3662fdc90bfe4a86b11499101b298ecd | language  |

### operations

TODO

| id | device_id | timestamp | type | created_at | object_type | object_parameters |
| -- | --------- | --------- | ---- | ---------- | ----------- | ----------------- |

### response_types

TODO:

| id                               | name  |
| -------------------------------- | ----- |
| 5b4f816026f511e2aac3001e52fffe46 | basic |

### responses

This stores data similar to the scheduling information stored in the `cards` table, along with some additional info:

| device_id                        | knol_id                          | deck_id                          | layout_id                        | duration_ms | created_at               | score             | score_mean        | score_standard_deviation | last_response_at     |
| -------------------------------- | -------------------------------- | -------------------------------- | -------------------------------- | ----------- | ------------------------ | ----------------- | ----------------- | ------------------------ | -------------------- |
| fdeb4ecfea1a4259ba2879aad0645642 | 0012a6ae0a0847838937fcbd18ea16d1 | 3afcf396cad54ddd83cbbce87ec72fb0 | acf3bd5e3fc94d64a9b21d7a531a6563 | 7248        | 2021-12-03T07:33:34.973Z | 0.75              | 0.830052375793457 | 0.0957268849015236       | 2021-07-13T17:16:13Z |
| fdeb4ecfea1a4259ba2879aad0645642 | 0012a6ae0a0847838937fcbd18ea16d1 | 3afcf396cad54ddd83cbbce87ec72fb0 | acf3bd5e3fc94d64a9b21d7a531a6563 | 3530        | 2021-12-03T07:34:03.144Z | 0.769999980926514 | 0.790026187896729 | 0.0786378681659699       | 2021-12-03T07:33:34Z |

TODO: explain.

### subscriptions

TODO: this is apparently has something to do with shared decks?

| deck_id                          | modified_at              | deck_name | deck_description | user_id                          |
| -------------------------------- | ------------------------ | --------- | ---------------- | -------------------------------- |
| a4dde94984644cf3a749a1898e47261c | 2020-06-28T21:17:30.239Z | Geography |                  | deadbeefdeadbeefdeadbeefdeadbeef |
| 3662fdc90bfe4a86b11499101b298ecd | 2020-07-13T17:14:10.219Z | English   |                  | deadbeefdeadbeefdeadbeefdeadbeef |

[^1]: "knol" is probably a reference to [Knol](https://en.wikipedia.org/wiki/Knol).

## Security

### Media

AnkiApp leaves users' media files exposed on its servers. Given a blob ID like 2e0957ca348e4e6ab480871628e59622,
the media file can be downloaded by simply accessing the URL https://blobs.ankiapp.com/2e0957ca348e4e6ab480871628e59622.

More context: https://forums.ankiweb.net/t/ankiapp-importer/16734/52

## API

Notes about the AnkiApp's API accessible from https://api.ankiapp.com

TODO: investigate using the API as an alternative method for importing.

### Cards data

Knol values are fetched by initiating a request like this:

https://api.ankiapp.com/decks/{deck_id}/knols/{knol_id}?client_version={ankiapp_version}&client_id={client_id}&t={token}
