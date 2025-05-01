document.addEventListener('DOMContentLoaded', function () {
  const cards = document.querySelectorAll('.card');

  cards.forEach(card => {
    // Create close button
    const closeBtn = document.createElement('span');
    closeBtn.classList.add('close-btn');
    closeBtn.innerHTML = '&times;';
    const cardBody = card.querySelector('.card-body');
    if (cardBody) cardBody.prepend(closeBtn);

    // Close action
    closeBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      card.classList.remove('expanded');
    });

    // Expand action
    card.addEventListener('click', function () {
      // Prevent toggling on close click
      if (event.target.classList.contains('close-btn')) return;

      // Collapse others first
      document.querySelectorAll('.card.expanded').forEach(c => {
        if (c !== card) c.classList.remove('expanded');
      });

      // Toggle this card
      this.classList.toggle('expanded');

      // Redraw Plotly chart if needed
      if (this.classList.contains('expanded')) {
        const chart = this.querySelector('.chart-container > div');
        if (chart && typeof Plotly !== 'undefined') {
          Plotly.Plots.resize(chart);
        }
      }
    });
  });
});
