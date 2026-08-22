/* 스크롤 등장 애니메이션
   IntersectionObserver로 요소가 화면에 들어오는 순간을 감지해
   .is-revealed 클래스를 붙인다. 한 번 나타난 요소는 관찰을 해제해
   불필요한 연산을 줄인다. */
document.addEventListener("DOMContentLoaded", function () {
  const observerOptions = {
    threshold: 0.1,                     // 10%만 보여도 등장으로 간주
    rootMargin: "0px 0px -50px 0px",    // 화면 아래쪽 50px은 미리 제외
  };

  const observer = new IntersectionObserver(function (entries, observer) {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-revealed");
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  document.querySelectorAll(".reveal-on-scroll").forEach((element) => {
    observer.observe(element);
  });
});