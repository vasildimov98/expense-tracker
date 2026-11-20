"""Human review of pending expense proposals (Lab 8, Task 2). This is the ONLY place approval happens.

    python -m app.ai.labs.lab08_review                    list pending proposals
    python -m app.ai.labs.lab08_review approve <id>       approve (type the digest you were shown), then execute
    python -m app.ai.labs.lab08_review reject <id>

The approver identity is your OS user (override with --as). It must differ from the proposer.
Needs PROPOSALS_PATH, the same file the chat process writes to.
"""
import argparse
import getpass
import sys

from app.ai import advisor_tools, proposals
from app.services.expense_service import ExpenseService
from app.storage import JsonExpenseStorage


def _show(p: proposals.Proposal) -> None:
    print(f"id:       {p.id}\nproposer: {p.actor}\ndigest:   {p.digest}\npayload:  {p.payload}\n")


def main(argv=None, ask=input, service=None) -> int:
    parser = argparse.ArgumentParser(prog="lab08_review")
    parser.add_argument("action", nargs="?", choices=["approve", "reject"])
    parser.add_argument("proposal_id", nargs="?")
    parser.add_argument("--as", dest="approver", default=getpass.getuser())
    args = parser.parse_args(argv)

    if not proposals._path():
        print("PROPOSALS_PATH is not set: the chat and this tool cannot share proposals.")
        return 2

    if args.action is None:
        pending = proposals.list_pending()
        for p in pending:
            _show(p)
        print(f"{len(pending)} pending")
        return 0

    try:
        if args.action == "reject":
            proposals.reject(args.proposal_id, args.approver)
            print("rejected")
            return 0
        proposals.list_pending()                       # refresh state from the file
        p = proposals._proposals.get(args.proposal_id)
        if p is None:
            print("unknown proposal")
            return 1
        _show(p)
        # Typing the digest proves you looked at what you approve; it is what approve() compares.
        typed = ask("Type the digest to approve: ").strip()
        proposals.approve(args.proposal_id, typed, args.approver)
        service = service or ExpenseService(JsonExpenseStorage(advisor_tools.EXPENSES_PATH))
        service.load_expenses()
        proposals.execute(args.proposal_id, service, executor=args.approver)
        print("approved and executed")
        return 0
    except proposals.ApprovalError as err:
        print(f"denied: {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
