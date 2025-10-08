<template>
  <div class="home">
    <h1>Submit Your Review</h1>

    <!-- Review Form -->
    <form @submit.prevent="submitReview" class="review-form">
      <textarea
        v-model="newReview"
        placeholder="Write a review..."
        rows="4"
      ></textarea>
      <button type="submit">
        Submit
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useReviewsStore } from '@/stores/reviews'

const reviewsStore = useReviewsStore()
const newReview = ref('')

const submitReview = async () => {
  if (!newReview.value.trim()) return
  await reviewsStore.addReview(newReview.value)
  newReview.value = ''
}
</script>
