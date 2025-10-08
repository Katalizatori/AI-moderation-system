
import { defineStore } from 'pinia'
import reviewService from '../services/reviewServices.js'

export const useReviewsStore = defineStore('reviews', {
  state: () => ({
    reviews: [],  // All reviews go here
    loading: false
  }),

  actions: {
    // Load reviews from Django
    async loadReviews() {
      this.loading = true
      try {
        this.reviews = await reviewService.getReviews()
        console.log('Loaded reviews:', this.reviews)
      } catch (error) {
        console.error('Failed to load reviews:', error)
      } finally {
        this.loading = false
      }
    },

    // Create new review
    async addReview(content) {
      const newReview = await reviewService.createReview(content)
      this.reviews.unshift(newReview)  // Add to top of list
    }
  }
})
