import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { KeyRound, Mail } from 'lucide-react'
import { api } from '../lib/api'

const DIGEST_MESSAGES: Record<string, string> = {
  smtp_not_configured: 'Email isn’t configured yet (set SMTP_* in the backend .env).',
  no_new_changes: 'No new changes since the last digest — nothing to send.',
}

export default function Settings() {
  const [apiKey, setApiKey] = useState(localStorage.getItem('argus_api_key') || '')
  const [savedKey, setSavedKey] = useState(false)

  const saveKey = () => {
    localStorage.setItem('argus_api_key', apiKey.trim())
    setSavedKey(true)
    setTimeout(() => setSavedKey(false), 1500)
  }

  const digest = useMutation({ mutationFn: api.sendDigest })

  const field = 'mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none'

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
      <p className="mt-1 text-sm text-slate-500">API access and digest email.</p>

      <section className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-slate-700">
          <KeyRound className="h-4 w-4" />
          <h2 className="font-semibold">API key</h2>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          Used by this dashboard and the Chrome extension to call the backend. It must match the
          backend's <code className="rounded bg-slate-100 px-1">API_KEY</code>. Leave blank if the
          backend has none.
        </p>
        <input
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="(no API key set)"
          className={field}
        />
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={saveKey}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            {savedKey ? 'Saved ✓' : 'Save key'}
          </button>
          <span className="text-xs text-slate-400">Stored locally in your browser.</span>
        </div>
      </section>

      <section className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-slate-700">
          <Mail className="h-4 w-4" />
          <h2 className="font-semibold">Digest email</h2>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          A digest of new intelligence — grouped by competitor, top 3 highlighted — is sent on a
          schedule (configured via <code className="rounded bg-slate-100 px-1">SMTP_*</code> and{' '}
          <code className="rounded bg-slate-100 px-1">DIGEST_*</code> in the backend). Send one now:
        </p>
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={() => digest.mutate()}
            disabled={digest.isPending}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {digest.isPending ? 'Sending…' : 'Send digest now'}
          </button>
          {digest.isSuccess && (
            <span className="text-sm text-slate-600">
              {digest.data.sent
                ? `Sent — ${digest.data.count} update(s).`
                : DIGEST_MESSAGES[digest.data.reason ?? ''] ?? 'Nothing to send.'}
            </span>
          )}
          {digest.isError && <span className="text-sm text-red-600">{(digest.error as Error).message}</span>}
        </div>
      </section>
    </div>
  )
}
