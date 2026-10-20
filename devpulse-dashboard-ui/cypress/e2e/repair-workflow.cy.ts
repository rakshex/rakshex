/// <reference types="cypress" />
import type { AxeStatic } from 'axe-core';

describe('Self-Repair source workflow and responsive navigation',()=>{
 function signIn(){
  const suffix=`${Date.now()}-${Cypress._.random(100000)}`;
  return cy.request('POST','/api/auth/register',{email:`job-${suffix}@test.test`,username:`job${Date.now()}`,password:'TestPass123!'}).then(response=>{
   return cy.request({method:'POST',url:'/api/teams/workspaces',headers:{Authorization:`Bearer ${response.body.token}`},body:{name:'Repair browser'}}).then(()=>{
    cy.visit('/self-repair',{onBeforeLoad(win){win.localStorage.setItem('devpulse_token',response.body.token);}});
   });
  });
 }
 it('plans a real repair, reviews a diff and reloads stored evidence without fabricating validation',()=>{
  signIn();cy.contains('button','Repair and validate').click();
  cy.contains('No repair jobs in this workspace yet.').should('be.visible');
  const schema=(key:string)=>({openapi:'3.0.3',paths:{'/v1/orders':{post:{requestBody:{content:{'application/json':{schema:{type:'object',properties:{[key]:{type:'string'}}}}}},responses:{'200':{description:'ok'}}}}}});
  const manifest={repository:'rakshex/rakshex',base_branch:'main',base_sha:'a'.repeat(40),before:schema('customer_ref'),after:schema('customer_id'),rule:{method:'POST',path:'/v1/orders',origin:'https://api.example.com',removed:'customer_ref',added:'customer_id',provenance:'https://example.com/migrations/customer-id'},files:{'client.py':"import requests\ndef create_order(customer):\n return requests.post('https://api.example.com/v1/orders',json={'customer_ref':customer})\n",'tests/test_client.py':"import sys,types,unittest\nfrom unittest.mock import Mock\nr=types.ModuleType('requests');r.post=Mock();sys.modules['requests']=r\nfrom client import create_order\nclass Regression(unittest.TestCase):\n def test_current_request(self):\n  create_order('synthetic')\n  r.post.assert_called_once_with('https://api.example.com/v1/orders',json={'customer_id':'synthetic'})\n"}};
  cy.contains('label','Repair manifest').find('textarea').type(JSON.stringify(manifest),{parseSpecialCharSequences:false,delay:0});
  cy.contains('button','Plan repair and queue validation').should('be.disabled');
  cy.get('input[type="checkbox"]').check();cy.contains('button','Plan repair and queue validation').click();
  cy.contains('Patch planned. Awaiting an isolated validation worker.').should('be.visible');
  cy.contains('button','Review patch').click();cy.get('pre[aria-label="Proposed patch"]').should('contain','customer_id');
  cy.contains('Approve draft PR publication').should('not.exist');
  cy.reload();cy.contains('button','Repair and validate').click();cy.contains('Patch planned. Awaiting an isolated validation worker.').should('be.visible');
  cy.contains('button','Delete repair data').click();cy.contains('No repair jobs in this workspace yet.').should('be.visible');
 });
 it('fits supported viewports and closes keyboard navigation with focus restored',()=>{
  signIn();
  [320,375,768,1024,1440].forEach(width=>{
   cy.viewport(width,900);cy.get('h1').should('be.visible');
   cy.readFile('../node_modules/axe-core/axe.min.js',{log:false}).then(script=>cy.window({log:false}).then(win=>{
    win.eval(script);
    return (win as unknown as {axe:AxeStatic}).axe.run(win.document.getElementById('main-content')!,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}}).then(result=>expect(result.violations.map(item=>item.id+': '+item.help)).to.deep.eq([]));
   }));
   cy.document().then(doc=>expect(doc.documentElement.scrollWidth).to.be.at.most(width));
   if(width<768){
    cy.get('button[aria-label="Open navigation"]').click();cy.get('[role="dialog"][aria-label="Navigation menu"]').should('be.visible');
    cy.get('button[aria-label="Close navigation"]').should('be.focused').type('{esc}');
    cy.get('[role="dialog"][aria-label="Navigation menu"]').should('not.exist');cy.get('button[aria-label="Open navigation"]').should('be.focused');
   }else cy.get('nav[aria-label="Primary navigation"]').should('be.visible');
  });
 });
});
