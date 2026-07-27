# Telegram feasibility spike

This small local tool is Comvoly's first technical proof of concept. It imports messages from one Telegram community that the signed-in account is authorised to access and stores them in a local SQLite database.

It does not yet provide a web interface, AI answers, cloud storage, or multi-user access. Those come after the basic import works reliably.

## Setup

1. Create a Telegram API application at `https://my.telegram.org` → **API development tools**.
2. Copy `.env.example` to `.env` and enter the values there. Do not share or commit `.env`.
3. Create and activate the local virtual environment, then install dependencies:

   ```cmd
   py -m venv .venv
   .venv\Scripts\activate
   py -m pip install -r requirements.txt
   ```

4. Run a small initial import:

   ```cmd
   py src\telegram_import.py --limit 50
   ```

Telegram will ask for the account phone number and its one-time sign-in code during the first run. The resulting local session file is ignored by Git.

## Security boundary

This importer must only be used for communities the signed-in Telegram account is authorised to access, and its local database is only for this development proof of concept.

## Re-importing and syncing

The importer is safe to run repeatedly. After the first history import, it only stores messages newer than the most recent Comvoly message for that community:

```cmd
.venv\Scripts\python.exe src\telegram_import.py
```

To import the complete available history on the test group, run this once:

```cmd
.venv\Scripts\python.exe src\telegram_import.py --full --limit 0
```

To keep Comvoly checking for new messages every two minutes while the laptop is on, run:

```cmd
.venv\Scripts\python.exe src\telegram_import.py --watch --interval 120
```

Press `Ctrl+C` to stop the local sync agent. It only imports messages newer than the latest one already stored by Comvoly.

The local search page can be started without Node.js or Next.js:

```cmd
py src\lite_app.py
```

## Grounded AI answers

Add `OPENAI_API_KEY` to `.env`. Configure the local owner sign-in once:

```cmd
.venv\Scripts\python.exe src\configure_owner.py
```

Choose a password with at least 12 characters. Comvoly stores a slow password hash,
not the password itself. Then start Comvoly with `src\Start Comvoly.cmd`.
The owner dashboard can interpret the imported archive and cites the supporting
messages inside Comvoly. Asking a question sends the included archive evidence to
the configured OpenAI model; API billing is separate from a ChatGPT subscription.

The testing defaults use GPT-5.6 Luna without additional reasoning and cap answers at
1,200 output tokens for lower latency and cost. Set `COMVOLY_AI_MODEL=gpt-5.6-terra`
and `COMVOLY_AI_REASONING=low` if representative questions need greater synthesis quality.
