const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
(async()=> {
 const browser=await chromium.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true,args:['--disable-gpu']});
 try {
  const page=await browser.newPage({viewport:{width:1180,height:900}});
  const errors=[]; page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(pathToFileURL('D:\\BrickMore\\Qwen_Comparision\\Results\\Qwen_AB_四项评分分析.html').href);
  for(const width of [1180,375]){
   await page.setViewportSize({width,height:900});
   const result=await page.evaluate(()=>({wide:document.documentElement.scrollWidth>window.innerWidth,images:[...document.images].every(i=>i.complete&&i.naturalWidth===512),title:document.title,sections:document.querySelectorAll('main>section').length}));
   if(result.wide||!result.images||result.sections!==6||errors.length)throw Error(JSON.stringify({result,errors}));
   console.log(width, result);
   if(width===1180)await page.screenshot({path:'D:\\BrickMore\\Results\\qwen_analysis_20261117\\report-preview.png'});
  }
  await page.locator('#levels summary').click();
  if(!await page.locator('#levels details').evaluate(e=>e.open)) throw Error('Details did not expand');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});

