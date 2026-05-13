// Mobile menu
const mobileMenuIcon = document.querySelector('.mobile-menu-icon');
const menuWrap = document.querySelector('.primary-menu-wrapper');
function showMobileMenu() {
  mobileMenuIcon.classList.toggle('menu-icon-active');
  menuWrap.classList.toggle('active-menu');
}
function closeMobileMenu() {
  mobileMenuIcon.classList.remove('menu-icon-active');
  menuWrap.classList.toggle('active-menu');
}
// Header search
const headerSearch = document.querySelector(".header-search");
function openSearch() {
  headerSearch.classList.toggle('header-search-active');
}
function closeSearch() {
  headerSearch.classList.remove('header-search-active');
}
// scroll to top
const scrollBtn = document.getElementById("scrollbutton");
if (scrollBtn) {
  window.onscroll = function() {
    if (document.documentElement.scrollTop > 80) {
      scrollBtn.style.display = "flex";
    } else {
      scrollBtn.style.display = "none";
    }
  }
}
function scrollToTop() {
  window.scrollTo({ top: 0 });
}
/* jQuery function */
jQuery(document).ready(function ($) {

// End document ready.  
});