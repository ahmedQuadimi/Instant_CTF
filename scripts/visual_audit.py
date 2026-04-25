#!/usr/bin/env python3
import argparse
import os
import re
import sys
import traceback
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

BASE_URL = "http://127.0.0.1:8000"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
MOBILE_VIEWPORT = {"width": 375, "height": 812}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = PROJECT_ROOT / "scripts" / "screenshots"
REPORT_PATH = PROJECT_ROOT / "scripts" / "visual_audit_report.md"


@dataclass
class PageResult:
    name: str
    url: str
    screenshot: str
    mobile_screenshot: str
    issues: list[str]

    @property
    def status(self) -> str:
        return "PASS" if not self.issues else "FAIL"


def sanitize_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "page"


def setup_django_and_get_ids() -> tuple[Any, int | None, int | None, int | None]:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Instant_CTF.settings")
    import django

    django.setup()
    from django.contrib.auth import get_user_model
    from Events.models import Event
    from Organizations.models import Organization
    from Teams.models import Team

    User = get_user_model()
    event_id = Event.objects.first().pk if Event.objects.exists() else None
    team_id = Team.objects.first().pk if Team.objects.exists() else None
    org_id = Organization.objects.first().pk if Organization.objects.exists() else None
    return User, event_id, team_id, org_id


def ensure_login_user(User: Any, email: str, password: str) -> None:
    user = User.objects.filter(email=email).first()
    if user is None:
        username = email
        if hasattr(User, "USERNAME_FIELD") and User.USERNAME_FIELD != "email":
            username = email.split("@")[0]
        create_kwargs: dict[str, Any] = {"email": email}
        if User.USERNAME_FIELD not in create_kwargs:
            create_kwargs[User.USERNAME_FIELD] = username
        user = User.objects.create_superuser(password=password, **create_kwargs)
        user.save()
        return

    # Ensure password is known so Playwright can sign in.
    if not user.check_password(password):
        user.set_password(password)
        user.save(update_fields=["password"])


def build_page_list(event_id: int | None, team_id: int | None, org_id: int | None) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    public_pages = [
        ("home_public", "/"),
        ("events_public", "/events/"),
        ("teams_public", "/teams/"),
        ("orgs_public", "/orgs/"),
        ("about", "/about/"),
        ("accounts_login", "/accounts/login/"),
        ("accounts_signup", "/accounts/signup/"),
        ("dev_index", "/dev/"),
        ("dev_components", "/dev/components/"),
        ("dev_auth", "/dev/auth/"),
        ("dev_forms", "/dev/forms/"),
        ("dev_challenges", "/dev/challenges/"),
        ("dev_scoreboard", "/dev/scoreboard/"),
        ("dev_events", "/dev/events/"),
    ]

    auth_pages = [
        ("home_authenticated", "/"),
        ("accounts_players", "/accounts/players/"),
        ("events_authenticated", "/events/"),
        ("events_create", "/events/create/"),
        ("teams_create", "/teams/create/"),
        ("orgs_create", "/orgs/create/"),
    ]

    if event_id is not None:
        auth_pages.extend(
            [
                (f"event_{event_id}", f"/events/{event_id}/"),
                (f"event_{event_id}_challenges", f"/events/{event_id}/challenges/"),
                (f"event_{event_id}_scoreboard", f"/events/{event_id}/scoreboard/"),
                (f"event_{event_id}_teams", f"/events/{event_id}/teams/"),
                (f"event_{event_id}_users", f"/events/{event_id}/users/"),
                (f"event_{event_id}_manage", f"/events/{event_id}/manage/"),
            ]
        )

    if team_id is not None:
        auth_pages.append((f"team_{team_id}", f"/teams/{team_id}/"))

    if org_id is not None:
        auth_pages.append((f"org_{org_id}", f"/orgs/{org_id}/"))

    return public_pages, auth_pages


def _first_ten(values: list[str]) -> list[str]:
    return values[:10]


def collect_checks(page: Page) -> list[str]:
    issues: list[str] = []

    page.set_viewport_size(DESKTOP_VIEWPORT)
    page.wait_for_timeout(150)

    page_height = page.evaluate("document.body.scrollHeight")
    viewport_height = page.viewport_size["height"] if page.viewport_size else DESKTOP_VIEWPORT["height"]
    if not isinstance(page_height, (int, float)) or page_height <= (viewport_height * 0.5):
        issues.append(f"[LAYOUT] Page appears too short (height={page_height}, viewport={viewport_height}).")

    try:
        footer_visible = page.locator("footer").first.is_visible(timeout=1000)
    except Exception:
        footer_visible = False
    if not footer_visible:
        issues.append("[LAYOUT] Footer is not visible.")

    try:
        nav_visible = page.locator("nav").first.is_visible(timeout=1000)
    except Exception:
        nav_visible = False
    if not nav_visible:
        issues.append("[LAYOUT] Nav is not visible.")

    desktop_no_horizontal = page.evaluate(
        """() => {
            if (document.body.scrollWidth <= window.innerWidth + 1) {
                return true;
            }
            const els = document.querySelectorAll('body *');
            for (const el of els) {
                if (el.closest('[aria-hidden="true"]')) continue;
                const rect = el.getBoundingClientRect();
                if (rect.right > window.innerWidth + 1 || rect.left < -1) {
                    return false;
                }
            }
            return true;
        }"""
    )
    if not desktop_no_horizontal:
        issues.append("[LAYOUT] Horizontal scrollbar detected.")

    h1_count = page.locator("h1").count()
    if h1_count <= 0:
        issues.append("[TYPOGRAPHY] No h1 found on page.")

    small_text = page.evaluate(
        """() => {
            const els = document.querySelectorAll('*');
            const small = [];
            els.forEach((el) => {
                const text = (el.textContent || '').trim();
                if (!text) return;
                const fs = parseFloat(window.getComputedStyle(el).fontSize);
                if (!Number.isNaN(fs) && fs < 12) {
                    small.push(el.tagName + ': ' + fs);
                }
            });
            return small.slice(0, 10);
        }"""
    )
    if small_text:
        issues.append(f"[TYPOGRAPHY] Elements with font-size below 12px: {', '.join(_first_ten(small_text))}.")

    white_backgrounds = page.evaluate(
        """() => {
            const els = document.querySelectorAll('*');
            const white = [];
            els.forEach((el) => {
                const bg = window.getComputedStyle(el).backgroundColor;
                if (bg === 'rgb(255, 255, 255)') {
                    const ident = (el.className && String(el.className).trim()) || el.tagName;
                    white.push(ident);
                }
            });
            return white.slice(0, 10);
        }"""
    )
    if white_backgrounds:
        issues.append(f"[COLOR] White backgrounds detected: {', '.join(_first_ten(white_backgrounds))}.")

    form_count = page.locator("form").count()
    csrf_count = page.locator('input[name="csrfmiddlewaretoken"]').count()
    if form_count > 0 and csrf_count != form_count:
        issues.append(f"[FORM] CSRF token count mismatch (forms={form_count}, csrf={csrf_count}).")

    border_gray_inputs = page.evaluate(
        """() => {
            const inputs = document.querySelectorAll('input, textarea, select');
            const offenders = [];
            inputs.forEach((el) => {
                const style = window.getComputedStyle(el);
                const borderColor = style.borderColor;
                if (borderColor === 'rgb(118, 118, 118)') {
                    const ident = el.name || el.id || el.className || el.tagName;
                    offenders.push(String(ident));
                }
            });
            return offenders.slice(0, 10);
        }"""
    )
    if border_gray_inputs:
        issues.append(
            f"[FORM] Inputs with default gray border (#767676): {', '.join(_first_ten(border_gray_inputs))}."
        )

    overflow_elements = page.evaluate(
        """() => {
            const els = document.querySelectorAll('*');
            const overflow = [];
            els.forEach((el) => {
                if (el.closest('[aria-hidden="true"]')) return;
                if (el.scrollWidth > el.offsetWidth + 2) {
                    overflow.push((el.className && String(el.className).trim()) || el.tagName);
                }
            });
            const uniq = [...new Set(overflow.filter(Boolean))];
            return uniq.slice(0, 10);
        }"""
    )
    if overflow_elements:
        issues.append(f"[SPACING] Horizontal overflow in elements: {', '.join(_first_ten(overflow_elements))}.")

    page.set_viewport_size(MOBILE_VIEWPORT)
    page.wait_for_timeout(250)
    mobile_no_horizontal = page.evaluate(
        """() => {
            if (document.body.scrollWidth <= window.innerWidth + 1) {
                return true;
            }
            const els = document.querySelectorAll('body *');
            for (const el of els) {
                if (el.closest('[aria-hidden="true"]')) continue;
                const rect = el.getBoundingClientRect();
                if (rect.right > window.innerWidth + 1 || rect.left < -1) {
                    return false;
                }
            }
            return true;
        }"""
    )
    if not mobile_no_horizontal:
        issues.append("[SPACING] Mobile viewport has horizontal overflow.")

    # Reset viewport for next page.
    page.set_viewport_size(DESKTOP_VIEWPORT)
    page.wait_for_timeout(150)

    return issues


def login(page: Page, email: str, password: str) -> None:
    page.set_viewport_size(DESKTOP_VIEWPORT)
    page.goto(f"{BASE_URL}/accounts/login/", wait_until="domcontentloaded")
    page.fill('input[name="login"]', email)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url(f"{BASE_URL}/", timeout=20000)


def audit_page(page: Page, name: str, path: str) -> PageResult:
    safe_name = sanitize_name(name)
    url = f"{BASE_URL}{path}"

    page.set_viewport_size(DESKTOP_VIEWPORT)
    response = page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(400)

    screenshot_name = f"{safe_name}.png"
    mobile_name = f"mobile_{safe_name}.png"

    desktop_path = SCREENSHOT_DIR / screenshot_name
    mobile_path = SCREENSHOT_DIR / mobile_name

    page.screenshot(path=str(desktop_path), full_page=True)

    page.set_viewport_size(MOBILE_VIEWPORT)
    page.wait_for_timeout(250)
    page.screenshot(path=str(mobile_path), full_page=True)

    # Run checks after screenshots unless this is an access-restricted page.
    status_code = response.status if response is not None else None
    if status_code == 403:
        issues = [
            "[LAYOUT] Access restricted (HTTP 403) for this account; known acceptable for non-organizer audit users."
        ]
    else:
        issues = collect_checks(page)

    return PageResult(
        name=safe_name,
        url=url,
        screenshot=f"screenshots/{screenshot_name}",
        mobile_screenshot=f"screenshots/{mobile_name}",
        issues=issues,
    )


def write_report(results: list[PageResult]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_pages = len(results)
    failed_pages = [r for r in results if r.status == "FAIL"]
    total_issues = sum(len(r.issues) for r in results)

    grouped: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for result in results:
        for issue in result.issues:
            category_match = re.match(r"\[(.*?)\]\s*(.*)", issue)
            if category_match:
                category = category_match.group(1)
                desc = category_match.group(2)
            else:
                category = "OTHER"
                desc = issue
            grouped[category][desc].add(result.name)

    lines: list[str] = []
    lines.append("# Visual Audit Report — Instant CTF")
    lines.append(f"Generated: {now}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Pages audited: {total_pages}")
    lines.append(f"- Pages with issues: {len(failed_pages)}")
    lines.append(f"- Total issues found: {total_issues}")
    lines.append("")
    lines.append("## Results by Page")
    lines.append("")

    for result in results:
        lines.append(f"### {result.name} — {result.url}")
        lines.append(f"Screenshot: {result.screenshot}")
        lines.append(f"Mobile screenshot: {result.mobile_screenshot}")
        lines.append(f"Status: {result.status}")
        lines.append("")
        lines.append("Issues found:")
        if result.issues:
            for issue in result.issues:
                lines.append(f"- {issue}")
        else:
            lines.append("No issues detected.")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## All Issues Summary (for fixing)")
    if not grouped:
        lines.append("No issues detected across audited pages.")
    else:
        ordered_categories = ["LAYOUT", "COLOR", "TYPOGRAPHY", "FORM", "SPACING", "OTHER"]
        for category in ordered_categories:
            if category not in grouped:
                continue
            lines.append(f"### {category}")
            for desc, pages in sorted(grouped[category].items(), key=lambda kv: kv[0]):
                page_list = ", ".join(sorted(pages))
                lines.append(f"- {desc} | Affected pages: {page_list}")
            lines.append("")

    content = "\n".join(lines).rstrip() + "\n"
    REPORT_PATH.write_text(content, encoding="utf-8")
    return content


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run visual audit with Playwright screenshots and checks.")
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Optional page names to audit (matching internal names like home_public or events_create).",
    )
    parser.add_argument("--email", default=os.getenv("AUDIT_EMAIL", "admin@test.com"), help="Login email")
    parser.add_argument(
        "--password",
        default=os.getenv("AUDIT_PASSWORD", "testpass123"),
        help="Login password",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium in headless mode (headed is default).",
    )
    return parser.parse_args()


def filter_pages(
    public_pages: list[tuple[str, str]], auth_pages: list[tuple[str, str]], only: list[str] | None
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    if not only:
        return public_pages, auth_pages
    wanted = {sanitize_name(v) for v in only}
    filtered_public = [(n, p) for n, p in public_pages if sanitize_name(n) in wanted]
    filtered_auth = [(n, p) for n, p in auth_pages if sanitize_name(n) in wanted]
    return filtered_public, filtered_auth


def main() -> int:
    args = parse_args()

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    User, event_id, team_id, org_id = setup_django_and_get_ids()
    ensure_login_user(User, args.email, args.password)

    public_pages, auth_pages = build_page_list(event_id, team_id, org_id)
    public_pages, auth_pages = filter_pages(public_pages, auth_pages, args.only)

    if not public_pages and not auth_pages:
        print("No pages selected for audit.")
        return 1

    results: list[PageResult] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(viewport=DESKTOP_VIEWPORT)
        page = context.new_page()

        # Public pages first.
        for name, path in public_pages:
            try:
                print(f"Auditing public page: {name} ({path})")
                results.append(audit_page(page, name, path))
            except Exception as exc:
                traceback.print_exc()
                screenshot_name = f"{sanitize_name(name)}.png"
                mobile_name = f"mobile_{sanitize_name(name)}.png"
                results.append(
                    PageResult(
                        name=sanitize_name(name),
                        url=f"{BASE_URL}{path}",
                        screenshot=f"screenshots/{screenshot_name}",
                        mobile_screenshot=f"screenshots/{mobile_name}",
                        issues=[f"[LAYOUT] Exception while auditing: {exc}"],
                    )
                )

        # Login before authenticated pages.
        if auth_pages:
            try:
                print("Logging in for authenticated pages...")
                login(page, args.email, args.password)
            except PlaywrightTimeoutError:
                browser.close()
                raise RuntimeError("Login failed: timeout waiting for redirect to home page.")

        for name, path in auth_pages:
            try:
                print(f"Auditing authenticated page: {name} ({path})")
                results.append(audit_page(page, name, path))
            except Exception as exc:
                traceback.print_exc()
                screenshot_name = f"{sanitize_name(name)}.png"
                mobile_name = f"mobile_{sanitize_name(name)}.png"
                results.append(
                    PageResult(
                        name=sanitize_name(name),
                        url=f"{BASE_URL}{path}",
                        screenshot=f"screenshots/{screenshot_name}",
                        mobile_screenshot=f"screenshots/{mobile_name}",
                        issues=[f"[LAYOUT] Exception while auditing: {exc}"],
                    )
                )

        browser.close()

    report_content = write_report(results)
    print(f"Report written to: {REPORT_PATH}")
    print(report_content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
