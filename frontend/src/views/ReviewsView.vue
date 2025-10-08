<template>
  <div class="reviews">
    <h1>All Reviews</h1>

    <div v-if="reviewsStore.loading">Loading reviews...</div>

    <div v-else class="reviews-list">
      <div
        v-for="review in allowedReviews"
        :key="review.id"
        class="review-card"
      >
        <p class="review-content">{{ review.content }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useReviewsStore } from '@/stores/reviews'

const reviewsStore = useReviewsStore()

// Load all reviews on mount
onMounted(() => {
  reviewsStore.loadReviews()
})

// Only display allowed reviews
const allowedReviews = computed(() =>
  reviewsStore.reviews.filter(r => r.status === 'allowed')
)
</script>
