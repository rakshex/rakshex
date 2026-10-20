/// <reference types="cypress" />

describe('RaksHex Dashboard', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('loads the dashboard with RaksHex branding and Self-Repair navigation', () => {
    cy.contains('Dashboard').should('be.visible');
    cy.contains('RaksHex').should('exist');
    cy.contains('Self-Repair').should('exist');
  });

  it('displays overview section', () => {
    cy.contains('Get Started with RaksHex').should('be.visible');
  });

  it('shows security score section', () => {
    cy.contains('Security Score').should('exist');
    cy.contains('Run Security Scan').should('exist');
  });

  it('shows cost intelligence section', () => {
    cy.contains('Cost Intelligence').should('exist');
  });

  it('shows additional links section', () => {
    cy.scrollTo('bottom');
    cy.contains('API Docs').should('exist');
  });

  it('shows health monitor', () => {
    cy.contains('Health Monitor').should('exist');
  });

  it('shows billing panel', () => {
    cy.contains('Billing').should('exist');
  });

  it('shows truthful backend connection status', () => {
    cy.scrollTo('bottom');
    cy.contains('Backend connected').should('be.visible');
    cy.contains('API connection').should('exist');
  });
});
