/// <reference types="cypress" />

/** Real browser → Next.js proxy → FastAPI → DB flow; no intercepted success. */
describe('Self-Repair contract-analysis intake', () => {
  it('creates a workspace, analyzes consented contracts and reloads persisted evidence', () => {
    const suffix = `${Date.now()}-${Cypress._.random(1000000)}`;
    cy.request('POST', '/api/auth/register', {email:`repair-${suffix}@test.test`,username:`repair${Date.now()}`,password:'TestPass123!'}).then(response => {
      expect(response.body.status).to.eq('success');
      cy.visit('/self-repair', {onBeforeLoad(win) {win.localStorage.setItem('devpulse_token',response.body.token);}});
    });
    cy.contains('Create your first workspace').should('be.visible');
    cy.get('input').filter('[maxlength="100"]').type(`Repair ${suffix}`);
    cy.contains('button','Create workspace').click();
    cy.contains('No analyses in this workspace yet.').should('be.visible');
    const before = {openapi:'3.0.3',paths:{'/orders':{get:{responses:{'200':{description:'ok'}}}}}};
    const after = {openapi:'3.0.3',paths:{}};
    cy.get('textarea').eq(0).type(JSON.stringify(before),{parseSpecialCharSequences:false});
    cy.get('textarea').eq(1).type(JSON.stringify(after),{parseSpecialCharSequences:false});
    cy.contains('button','Analyze contracts').should('be.disabled');
    cy.get('input[type="checkbox"]').check();
    cy.contains('button','Analyze contracts').click();
    cy.contains('Human review required').should('be.visible');
    cy.contains('operation_removed').should('be.visible');
    cy.reload();
    cy.contains('button','1 operation changes').click();
    cy.contains('Human review required').should('be.visible');
    cy.contains('button','Delete evidence').click();
    cy.contains('No analyses in this workspace yet.').should('be.visible');
  });
});
