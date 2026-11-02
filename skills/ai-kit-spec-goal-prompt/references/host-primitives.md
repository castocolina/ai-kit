# Host primitives

What each primitive label means, and what is known about each supported host.

Load when: before relaying any primitive label from the detect output (SKILL.md §2), or when the
user asks which host can run a goal, a loop or a schedule.

## The two labels

Every primitive row in detect's `primitives` carries two labels.

- `availability`:
  - `available`: the current host meets the row's version floor, or a tool row's name was in the
    `--tools` list. Only the current host can produce `available`.
  - `not seen`: a tool row whose name was not in `--tools`. It means "this session did not see
    it", never "absent".
  - `absent`: only on the `none` row, when `--help` was read and shows no goal, loop, schedule or
    cron keyword.
  - `unverified`: everything else: a non-current host, a version below the floor, a failed probe,
    or a missing sibling CLI.
- `usage_source`: where the usage claim comes from.
  - `official docs`: Claude's goal and scheduled-task pages, fetched during research (cited).
  - `live`: observed by a probe (a `--help` grep, or a spike run).
  - `binary strings`: strings found in an installed binary; the syntax is reverse-engineered.
  - `unverified`: no source.

Rule: `not seen`, `absent` and `unverified` are not available. Relay them with their label.

## Hosts

Detect's target is one of `claude`, `codex`, `opencode`, `pi`, `cursor`. Facts per host:

- `claude`: `/goal` is documented, with a version floor of 2.1.139 (official docs). The installed
  binary holds the `/goal`, `/loop`, `CronCreate`, `ScheduleWakeup` and `RemoteTrigger` strings
  (binary strings). Tool rows (`CronCreate`, `ScheduleWakeup`, `Monitor`, `RemoteTrigger`,
  `PushNotification`) are `available` only when their names are in `--tools`, else `not seen`.
  `/loop` is a bundled skill with no version floor, so it reads `unverified`.
- `codex`: `/goal [<objective>|clear|edit|pause|resume]` (reverse-engineered syntax; sources in
  [evidence](evidence.md)). Research ran `codex features list`, which printed
  `goals stable true`; detect still labels codex rows `unverified`, because codex is not the
  current host. No schedule or loop keyword was found.
- `opencode`: research read `opencode --help` and `opencode run --help`; neither carries a goal,
  loop, schedule, cron or ralph keyword (live). Community wrappers are unchecked.
- `pi`: `pi --help` carries no such keyword (live). Third-party schedulers are
  unchecked.
- `cursor`: detect maps this target to the `agent` binary (`HOST_BINARY`). Research probed
  `cursor-agent --help` and found no such keyword (live). Its name differs from
  the binary name, so check the binary name before you cite it.

A non-current target host is `unverified` in every row. That is a rule of the detect code, not a
finding about the host.

## How `--tools` is built

Pass the names of the tools you can see in your own tool list, plus the result of one `ToolSearch`
keyword query (`cron schedule wakeup loop`) when your host has `ToolSearch`. Pass only names you
saw. A name the matrix does not know is listed in `unrecognized_tools`; a known name you did not
pass reads `not seen`.

## Survival flags

The matrix rows carry `survives_stall`, `survives_process_death` and `survives_reboot`. They are
data from the session-wake matrix. This skill does not re-measure them on a host.

## Unverified

- Every non-current host's rows: `unverified` by rule, with no live check of that host here.
- Community wrappers for opencode, pi and cursor: not checked.
- The survival flags of each row: taken from data, not measured per host.
