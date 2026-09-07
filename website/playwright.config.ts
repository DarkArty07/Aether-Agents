import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir:'./tests/browser',
  timeout:60000,
  fullyParallel:true,
  workers:2,
  reporter:[['list'],['html',{open:'never'}]],
  use:{baseURL:'http://127.0.0.1:4321',trace:'retain-on-failure'},
  webServer:{command:'npm run preview',url:'http://127.0.0.1:4321',reuseExistingServer:!process.env.CI,timeout:30000},
  projects:[
    {name:'desktop',use:{...devices['Desktop Chrome'],viewport:{width:1440,height:1000}}},
    {name:'mobile',use:{...devices['Pixel 7'],viewport:{width:390,height:844}}},
  ],
});
