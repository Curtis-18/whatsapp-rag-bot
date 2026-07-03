# WhatsApp RAG Bot

A WhatsApp bot that answers questions using only your own documents (RAG:
Retrieve, Augment, Generate). Built with FastAPI, Claude, Voyage AI
embeddings, and Qdrant.

**This version of the README assumes you are NOT installing Python or
running anything on your own PC.** Everything runs on Render's servers.
Your PC only needs a browser. If you'd rather run it locally on a capable
machine, an older version of this guide covers that, ask if you want it.

---

## Project file structure

This is what's inside the zip. Keep this exact folder layout when you
upload it to GitHub, the code refers to files by these paths.

```
whatsapp-rag-bot/
├── app/
│   ├── __init__.py       (empty, just marks this folder as a package)
│   ├── config.py          (loads all your secrets from environment variables)
│   ├── embeddings.py       (talks to Voyage AI, turns text into vectors)
│   ├── vectorstore.py       (talks to Qdrant, stores/searches those vectors)
│   ├── rag.py                (the core logic: retrieve chunks, ask Claude)
│   ├── whatsapp.py            (sends replies, checks webhook signatures)
│   └── main.py                  (the FastAPI app, this is what Render runs)
├── scripts/
│   ├── __init__.py
│   └── ingest.py           (chunks + embeds knowledge_base/, run automatically)
├── knowledge_base/
│   └── example.txt          (placeholder, replace with your real documents)
├── requirements.txt          (list of Python packages Render installs)
├── .env.example                (template showing which secrets you need)
├── .gitignore
└── README.md                    (this file)
```

You will never run any of these files yourself. You upload them to GitHub,
Render reads them and runs `app/main.py`, and `scripts/ingest.py` runs
automatically inside Render when needed (details in Step 5).

---

## Architecture, and why each piece was chosen

```
WhatsApp user
     |
     v
Meta WhatsApp Cloud API  (message transport, official, free for this use case)
     |  webhook POST
     v
FastAPI app on Render     (your code, always-on web service)
     |
     +--> Voyage AI        (turns the question into a vector)
     |
     +--> Qdrant Cloud      (finds the closest matching chunks of your docs)
     |
     +--> Claude (Anthropic API)   (writes the answer, using only those chunks)
     |
     v
Meta WhatsApp Cloud API  (sends the reply back)
```

- **WhatsApp Cloud API, not a paid BSP (Twilio/360dialog/Wati)**: it's the
  direct, official channel from Meta, no middleman markup. A bot that only
  replies to messages people send it falls inside what Meta calls a
  "service conversation", which is free and uncapped. You'd only pay Meta
  if you proactively messaged people outside a 24-hour window, which this
  bot doesn't do.
- **Voyage AI for embeddings, not OpenAI**: Anthropic doesn't have its own
  embedding model and officially recommends Voyage AI. Every account gets
  200 million free tokens on `voyage-4-lite`, far more than a small
  knowledge base will ever use, so this is effectively free.
- **Qdrant Cloud for the vector database**: the free tier (1GB RAM, 4GB
  disk) is permanent, not a trial, and comfortably holds far more than a
  personal or organisational knowledge base needs.
- **Claude Haiku 4.5 as the default model**: RAG quality depends mostly on
  retrieval, not on the size of the model writing the final sentence.
  Haiku is fast and cheap. Swap `CLAUDE_MODEL` to `claude-sonnet-5` in
  Render's environment variables any time you want deeper reasoning.
- **Render for hosting, not Railway**: Railway removed its free tier;
  you're billed from the first minute. Render still has a genuine free
  web service tier. The tradeoff: a free Render service sleeps after
  inactivity and takes a few seconds to wake up, Meta simply retries the
  webhook if the first response is slow, so this is a fine tradeoff.

---

## Step 1: Create the accounts you'll need

All done through a browser, a few minutes each:

1. **Meta Developer account**: https://developers.facebook.com
2. **Anthropic Console account**: https://console.anthropic.com
3. **Voyage AI account**: https://dash.voyageai.com
4. **Qdrant Cloud account**: https://cloud.qdrant.io
5. **Render account**: https://render.com (sign up with GitHub, makes
   deployment a one-click connection later)
6. **GitHub account**: https://github.com

---

## Step 2: Upload the project to GitHub

1. On github.com, click the **+** top right, **New repository**. Name it
   `whatsapp-rag-bot`, private or public, either works. Click **Create
   repository**.
2. On the empty repo page, click **Add file > Upload files**.
3. Unzip the file I gave you first (right-click it on Windows, **Extract
   All**), then drag the whole extracted `whatsapp-rag-bot` folder from
   File Explorer into that browser window. GitHub preserves the folder
   structure automatically.
4. Scroll down, write a commit message like "Initial upload", click
   **Commit changes**.

Your code is now on GitHub. You will never need to touch `git` commands.

---

## Step 3: Set up the WhatsApp Cloud API

The fiddliest part because it's Meta's dashboard, not code.

1. Go to https://developers.facebook.com/apps, click **Create App**,
   choose **Business** as the app type.
2. You'll be prompted to **Add products**, find **WhatsApp**, click
   **Set up**.
3. Attach or create a **Business Portfolio** when asked, either is fine
   for testing.
4. On the **WhatsApp > API Setup** page, note down:
   - The **Phone Number ID** for the test number Meta gives you.
   - The **temporary access token** (valid ~24 hours, fine for now).
5. Under **Send and receive messages**, add your own WhatsApp number as a
   recipient (you'll get a code on WhatsApp to confirm it).
6. Note your **App Secret**: App Dashboard > App Settings > Basic.

Keep this tab open, you'll come back to it after deploying.

---

## Step 4: Get your Claude, Voyage, and Qdrant credentials

1. **Claude**: console.anthropic.com > **API Keys** > Create Key.
2. **Voyage AI**: dash.voyageai.com > **API Keys** > Create.
3. **Qdrant Cloud**: cloud.qdrant.io > **Create Cluster** > **Free** tier >
   any region. Once ready, open **Data Access Control** to generate an API
   key, and copy the cluster URL (looks like
   `https://xxxxx.aws.cloud.qdrant.io:6333`).

You should now have six values total: WhatsApp token, phone number ID,
app secret, Anthropic key, Voyage key, and Qdrant URL + key. Keep them
somewhere you can copy from, you're about to paste them into Render.

---

## Step 5: Deploy to Render (this is where the app actually runs)

1. On render.com: **New > Web Service**, connect the GitHub repo you
   uploaded in Step 2.
2. Settings:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Scroll to **Environment**, click **Add Environment Variable**, and add
   each of these one at a time (values from Steps 3 and 4):

   | Key | Value |
   |---|---|
   | `WHATSAPP_TOKEN` | your temporary access token |
   | `WHATSAPP_PHONE_NUMBER_ID` | your phone number ID |
   | `WHATSAPP_VERIFY_TOKEN` | make up any random string yourself |
   | `WHATSAPP_APP_SECRET` | your app secret |
   | `ANTHROPIC_API_KEY` | your Claude API key |
   | `VOYAGE_API_KEY` | your Voyage API key |
   | `QDRANT_URL` | your Qdrant cluster URL |
   | `QDRANT_API_KEY` | your Qdrant API key |

4. Click **Create Web Service**. Render installs everything and starts the
   app. Watch the **Logs** tab, you should see:
   ```
   No knowledge base in Qdrant yet, running first-time ingestion...
   knowledge_base/example.txt: 1 chunks
   Done. 1 chunks from 1 files stored in Qdrant.
   ```
   That's `scripts/ingest.py` running automatically on first boot, loading
   whatever is in `knowledge_base/` into Qdrant. You never ran it
   yourself, Render did it for you when the app started.
5. Once it says "Live", copy your URL, something like
   `https://whatsapp-rag-bot.onrender.com`.

---

## Step 6: Connect the webhook

1. Back in Meta's dashboard: **WhatsApp > Configuration > Edit** next to
   Webhook.
2. **Callback URL**: `https://your-app.onrender.com/webhook`
3. **Verify Token**: the exact string you set for `WHATSAPP_VERIFY_TOKEN`
   in Render.
4. Click **Verify and Save**. This should succeed instantly.
5. Under **Webhook fields**, click **Subscribe** next to `messages`.

Now message your test WhatsApp number from your phone. It should reply
using whatever is in `knowledge_base/`.

---

## Step 7: Replace the placeholder knowledge base with your real documents

The bot currently only knows the placeholder text in
`knowledge_base/example.txt`. To load your real documents:

1. On GitHub, open your repo, click into the `knowledge_base` folder.
2. Delete `example.txt` (open it, click the trash icon).
3. Click **Add file > Upload files**, drag in your real `.txt`, `.md`, or
   `.pdf` files (one topic per file works better than one giant file).
   Commit the change.
4. Render automatically redetects the GitHub push and redeploys, but
   redeploying alone does **not** refresh Qdrant (your old data stays
   until you tell it to reload). To refresh it, open this URL in your
   browser once the redeploy finishes:
   ```
   https://your-app.onrender.com/admin/reingest?token=YOUR_WHATSAPP_VERIFY_TOKEN
   ```
   (the same random string you used for `WHATSAPP_VERIFY_TOKEN`). You
   should get back something like:
   ```json
   {"status": "ok", "files": 3, "chunks": 41, "message": "Done. 41 chunks from 3 files stored in Qdrant."}
   ```

Repeat step 4 any time you add, remove, or edit files in `knowledge_base/`.
This is the one manual action you'll take regularly, everything else runs
by itself.

---

## Step 8: Get a permanent WhatsApp token

The temporary token from Step 3 expires in about 24 hours. Before this
goes live for real use:

1. Meta Business Settings > **System Users** > create a system user with
   admin access to your WhatsApp Business Account.
2. Generate a token with `whatsapp_business_messaging` permission and
   **no expiration**.
3. In Render, edit the `WHATSAPP_TOKEN` environment variable to this new
   token, save. Render redeploys automatically.

---

## Cost, realistically, at small scale

| Service | Cost |
|---|---|
| WhatsApp Cloud API | $0 (replies to inbound messages are free "service conversations") |
| Voyage AI embeddings | $0 (200M free tokens per account) |
| Qdrant Cloud | $0 (free tier, permanent, not a trial) |
| Render hosting | $0 (free tier; upgrade to $7/month to remove the cold-start sleep delay) |
| Claude API | Usage-based, a few cents per 100 conversations on Haiku 4.5 |

---

## If something isn't working

Open your Render dashboard, click your service, click **Logs**. Every
error shows up there in plain text, including anything printed by
`ingest.py` or a failed API call. This is your main debugging tool since
nothing runs on your own PC.

---

## Sensible next steps once this is working

- **Business verification** with Meta, to move off the test number and
  onto your own WhatsApp Business number.
- **Conversation memory**: right now every message is answered
  independently. Add short per-user chat history if you want follow-up
  questions to work.
- **Better chunking**: the current chunker splits by raw character count.
  For structured documents, splitting by heading or paragraph will improve
  retrieval quality.
