/**
 * Management Dashboard Tab Switching
 * Shared function available across all management pages
 */

const MANAGEMENT_TABS = ['teachers', 'classrooms', 'students', 'analytics', 'announcements'];

function switchMgmtTab(name) {
  // Validate tab name
  if (!MANAGEMENT_TABS.includes(name)) name = 'teachers';
  
  // Check if we're on the dashboard page
  const dashboardPage = document.querySelector('#tab-teachers') !== null;
  
  if (!dashboardPage) {
    // Not on dashboard - redirect to dashboard with tab hash
    window.location.href = '/management/dashboard/#' + name;
    return;
  }
  
  // We're on dashboard - switch tabs locally
  // Hide all panes
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  
  // Show selected pane
  const pane = document.getElementById('tab-' + name);
  if (pane) {
    pane.classList.add('active');
  }
  
  // Update active state on sidebar nav links
  document.querySelectorAll('.mgmt-nav-link').forEach(link => {
    const tabName = link.getAttribute('data-tab');
    if (tabName === name) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });
  
  // Update active state on dashboard tab-chip buttons
  document.querySelectorAll('.tab-chip').forEach(link => {
    const href = link.getAttribute('href');
    if (href === '#' + name) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });
  
  // Update URL hash
  history.replaceState(null, '', '#' + name);
}

// On page load: restore tab from URL hash
document.addEventListener('DOMContentLoaded', function() {
  const hash = window.location.hash.replace('#', '');
  if (MANAGEMENT_TABS.includes(hash)) {
    switchMgmtTab(hash);
  } else if (document.querySelector('#tab-teachers')) {
    // We're on dashboard, default to teachers tab
    switchMgmtTab('teachers');
  } else {
    // Mark the Teachers nav link as active by default when not on dashboard
    const teachersLink = document.querySelector('.mgmt-nav-link[data-tab="teachers"]');
    if (teachersLink) {
      teachersLink.classList.add('active');
    }
  }
});

// Handle hash change (browser back/forward or manual hash change)
window.addEventListener('hashchange', function() {
  const hash = window.location.hash.replace('#', '');
  if (MANAGEMENT_TABS.includes(hash)) {
    switchMgmtTab(hash);
  }
});
