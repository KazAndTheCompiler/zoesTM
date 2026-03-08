import { test, expect } from '@playwright/test';

test.describe('Full User Flow: Create Task → Schedule → Focus → Report → Review', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for the app to load and show overview
    await expect(page.getByTestId('overview-grid')).toBeVisible({ timeout: 10000 });
  });

  test('complete flow', async ({ page }) => {
    // 1) Create a task via quick add
    const quickInput = page.getByRole('textbox', { name: /add task/i });
    await quickInput.fill('E2E test task due tomorrow at 9am #e2e !high');

    const runButton = page.getByRole('button', { name: /Quick parse/i });
    await runButton.click();

    // Expect an alert with task details (as per current frontend)
    await expect(page).toHaveAlert(/task/i, { timeout: 5000 });
    const alertText = await page.onAlert((text) => text);
    // Dismiss alert
    page.onAlert(() => {});
    // Verify task was created by checking tasks count
    await expect(page.getByTestId('box-tasks')).toContainText(/Count: \d+/);

    // 2) Schedule: Navigate to calendar view and see the task
    await page.click('button:has-text("Calendar")');
    await expect(page).toHaveURL(/.*#\/calendar/);
    // The calendar should show entries; we can check the mode and entry count
    await expect(page.getByTestId('box-calendar')).toContainText(/Mode: day/);
    // Since our task is due tomorrow, it should appear in the entries
    // The backend calendar view returns entries; we can look for our task title in the box
    await expect(page.getByTestId('box-calendar')).toContainText(/E2E test task/);

    // 3) Focus: Start a Pomodoro session
    await page.click('button:has-text("Focus / Pomodoro")');
    await expect(page).toHaveURL(/.*#\/focus/);
    // Click Start 25
    await page.click('button:has-text("Start 25")');
    // Verify focus status changes to running
    await expect(page.getByTestId('box-focus')).toContainText(/Status: running/);
    // Countdown should show near 25:00
    await expect(page.getByTestId('box-focus')).toMatchText(/\d{2}:\d{2}/);

    // Complete the focus session (we'll use complete endpoint via UI, but there's no button in current UI)
    // In current App.tsx, there is a "Complete" button in FocusBox. Let's click it.
    await page.click('button:has-text("Complete")');
    // After some time status should become idle again (or maybe 'completed' but app resets)
    await expect(page.getByTestId('box-focus')).toContainText(/Status: idle|completed/);

    // 4) Report: In the current app, focus completion is reported via metrics; we can check that metrics endpoint works indirectly.
    // We'll skip explicit reporting UI since it's not implemented yet; instead move to review.

    // 5) Review: Open Anki review panel and answer a card
    await page.click('button:has-text("Review / Anki")');
    await expect(page).toHaveURL(/.*#\/review-anki/);
    // The session should show a card if any are due. If none, we can create one via API.
    // Ensure there is at least one card in the queue by creating one through API
    const apiUrl = '/review/decks';
    // Create a deck
    const deckResponse = await page.request.post(apiUrl, {
      data: { name: 'E2E Flow Deck' }
    });
    const deck = await deckResponse.json();
    expect(deckResponse.ok()).toBeTruthy();
    // Add a card
    await page.request.post(`${apiUrl}/${deck.id}/cards`, {
      data: { front: 'E2E Front', back: 'E2E Back', tags: 'e2e' }
    });
    // Start session
    const sessionResp = await page.request.post('/review/session/start?limit=5');
    const sessionData = await sessionResp.json();
    expect(sessionData.count).toBeGreaterThan(0);

    // Now we can answer a card using keyboard shortcut (3 for good)
    await page.keyboard.press('3');
    // Check that state updates (the box shows interval)
    await expect(page.getByTestId('box-review-anki')).toContainText(/Interval: \d+d/);
  });
});
