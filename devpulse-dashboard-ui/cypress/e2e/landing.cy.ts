/// <reference types="cypress" />

describe('RaksHex product page', () => {
  beforeEach(() => cy.visit('/landing'));

  it('presents the current API Change Intelligence direction', () => {
    cy.contains('See what changed in your API contract.').should('be.visible');
    cy.contains('Early implementation').should('be.visible');
  });
  it('links to the actual contract-analysis workflow', () => {
    cy.contains('a','Analyze contracts').should('have.attr','href','/self-repair');
  });
  it('states what is available without pretending the repair pipeline is complete', () => {
    cy.contains('Contract analysis available').should('be.visible');
    cy.contains('Code impact, patch validation and GitHub draft PRs are next.').should('exist');
  });
  it('shows the planned modules with explicit status', () => {
    cy.contains('Budget Lock').should('exist');
    cy.contains('LeakShield').should('exist');
    cy.contains('Controlled agent execution').should('exist');
    cy.contains('Security hardening pending').should('exist');
    cy.contains('Separate design track').should('exist');
  });
  it('explains the real intake workflow', () => {
    cy.contains('1. Authorize processing').should('exist');
    cy.contains('2. Compare operations').should('exist');
    cy.contains('3. Review the evidence').should('exist');
  });
  it('explains the input and retention boundary', () => {
    cy.contains('A clear processing boundary').should('exist');
    cy.contains('not raw specifications').should('exist');
  });
  it('has no fabricated savings or customer claims', () => {
    cy.contains('40%').should('not.exist');
    cy.contains('Join teams using').should('not.exist');
    cy.contains('Pricing and production release terms are not finalized.').should('exist');
  });
  it('links to the correct development repository', () => {
    cy.contains('a','View development source on GitHub').should('have.attr','href','https://github.com/rakshex/rakshex/tree/codex/rakshex-foundation-20261020');
  });
});
