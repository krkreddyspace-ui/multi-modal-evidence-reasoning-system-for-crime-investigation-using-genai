const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    console.log("Navigating to dashboard...");
    await page.goto('http://127.0.0.1:8000');

    console.log("Uploading file...");
    // Create a dummy file buffer
    const buffer = Buffer.from('this is a test evidence file');
    
    // Set files on the hidden input
    await page.setInputFiles('#file-input', {
        name: 'test.txt',
        mimeType: 'text/plain',
        buffer: buffer
    });

    console.log("Checking if button is enabled...");
    const disabled = await page.$eval('#analyze-btn', btn => btn.hasAttribute('disabled'));
    console.log("Button disabled state:", disabled);

    console.log("Clicking RUN ENGINE...");
    await page.click('#analyze-btn');

    console.log("Waiting for network response...");
    try {
        const response = await page.waitForResponse('/api/analyze', { timeout: 30000 });
        console.log("Response status:", response.status());
        const json = await response.json();
        console.log("Response JSON preview:", JSON.stringify(json).substring(0, 100));
    } catch (e) {
        console.log("Network wait error:", e);
    }
    
    // Check if error alert popped up
    page.on('dialog', async dialog => {
        console.log("Dialog message:", dialog.message());
        await dialog.accept();
    });

    // Check DOM changes
    const culprit = await page.$eval('#res-culprit', el => el.textContent);
    console.log("Resulting Culprit display:", culprit);

    await browser.close();
})();
