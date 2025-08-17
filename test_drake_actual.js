const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    
    // Enable console logging
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    
    await page.goto('http://localhost:8000/test_adp.html');
    
    // Click Load Data button
    await page.click('#loadBtn');
    await page.waitForTimeout(2000);
    
    // Test Public ADP
    await page.click('#publicBtn');
    await page.waitForTimeout(1000);
    
    // Get the public ADP value
    const publicResult = await page.evaluate(() => {
        const results = document.querySelector('.public');
        return results ? results.innerText : 'Not found';
    });
    
    console.log('\n=== PUBLIC MODE RESULTS ===');
    console.log(publicResult);
    
    // Test Private ADP
    await page.click('#privateBtn');
    await page.waitForTimeout(1000);
    
    // Get the private ADP value
    const privateResult = await page.evaluate(() => {
        const results = document.querySelector('.private');
        return results ? results.innerText : 'Not found';
    });
    
    console.log('\n=== PRIVATE MODE RESULTS ===');
    console.log(privateResult);
    
    await browser.close();
})();